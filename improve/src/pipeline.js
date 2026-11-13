// `ca-improve run`: discover -> collect -> distill -> analyze -> fold ->
// consolidate -> propose. Writes private state only; never touches the CA
// repo, tracked files, or live Hermes.

import path from "node:path";

import { analyzeTraces, loadContexts } from "./analyze.js";
import { consolidateLedger, saveOpenGaps } from "./consolidate.js";
import { distill } from "./distill.js";
import { foldEvidence } from "./fold.js";
import { discoverTranscripts, readTranscriptEvents, SUPPORTED_HARNESSES } from "./harnesses.js";
import { mockInvoke } from "./mock.js";
import { assertModelConfigured, modelInvoke } from "./model.js";
import { propose } from "./propose.js";
import { readSoulSnapshot } from "./soul.js";
import {
  assertMinGapEvidence,
  checkpointKey,
  evidenceFile,
  initStateDir,
  readEvidenceRecords,
  readJson,
  readSessionCheckpoint,
  timestampId,
  writeJson,
} from "./state.js";

/** An unreadable session becomes a failed trace, retried next run rather than checkpointed. */
async function collectTrace(transcript) {
  let events;
  try {
    events = await readTranscriptEvents(transcript);
  } catch (err) {
    return { transcriptId: transcript.id, harness: transcript.harness, readError: `unreadable session: ${err.message}` };
  }
  const count = (pred) => events.filter(pred).length;
  return {
    transcriptId: transcript.id,
    harness: transcript.harness,
    activity: {
      userTurns: count((e) => e?.kind === "message" && e.role === "user"),
      assistantTurns: count((e) => e?.kind === "message" && e.role === "assistant"),
      toolCalls: count((e) => e?.kind === "tool"),
    },
    distilled: distill(events, transcript),
  };
}

async function mapPool(items, jobs, fn) {
  const out = new Array(items.length);
  let next = 0;
  const worker = async () => {
    while (next < items.length) {
      const index = next++;
      out[index] = await fn(items[index]);
    }
  };
  await Promise.all(Array.from({ length: Math.max(1, Math.min(Number(jobs) || 4, items.length)) }, worker));
  return out;
}

/**
 * Header-only OpenCode stores need an `opencode export` per session, which
 * can take minutes for a large store. Bound that work with a newest-first
 * batch; checkpoints let later runs advance to the rest.
 */
function capOpencode(transcripts, max) {
  const opencode = transcripts.filter((t) => t.harness === "opencode").sort((a, b) => (b.mtimeMs || 0) - (a.mtimeMs || 0));
  if (!(Number.isInteger(max) && max > 0) || opencode.length <= max) return transcripts;
  const allowed = new Set(opencode.slice(0, max).map((t) => t.id));
  return transcripts.filter((t) => t.harness !== "opencode" || allowed.has(t.id));
}

function countByHarness(transcripts) {
  const counts = {};
  for (const t of transcripts) counts[t.harness] = (counts[t.harness] || 0) + 1;
  return counts;
}

/**
 * @param invoke `(role, prompt, context) => Promise<object>`; defaults to the
 *   mock or the configured model per `analyzer`. Tests inject their own.
 * @returns the proposal (also written to stateDir/proposal.json)
 */
export async function runPipeline({
  home,
  stateDir,
  soulPath,
  posturePath = null,
  experiencePath = null,
  since = "30d",
  harnesses = null,
  strictHarnesses = false,
  analyzer = "model",
  minGapEvidence = 2,
  invoke = null,
  progress = null,
  jobs = Number(process.env.CA_IMPROVE_JOBS || 4),
}) {
  const emit = (event, data = {}) => progress?.(event, data);
  const floor = assertMinGapEvidence(minGapEvidence, "minGapEvidence");
  if (!stateDir) throw new Error("improve-run: --state-dir is required");
  if (analyzer !== "model" && analyzer !== "mock") throw new Error(`improve-run: --analyzer must be model or mock (got ${JSON.stringify(analyzer)})`);
  const soul = readSoulSnapshot(soulPath);
  if (!invoke) {
    if (analyzer === "mock") invoke = mockInvoke;
    else {
      assertModelConfigured();
      invoke = modelInvoke(stateDir);
    }
  }
  initStateDir(stateDir);
  const runId = timestampId("run");

  emit("discover:start", { harnesses: harnesses || SUPPORTED_HARNESSES });
  const discovery = discoverTranscripts({ home, stateDir, since, harnesses, strict: strictHarnesses });
  const transcripts = capOpencode(discovery.transcripts, Number(process.env.CA_IMPROVE_MAX_OPENCODE_EXPORTS || 50));
  const perHarness = countByHarness(transcripts);
  emit("discover:done", { transcripts: transcripts.length, perHarness });

  emit("analyze:start", { total: transcripts.length, pending: transcripts.length, analyzer });
  const traces = await mapPool(transcripts, jobs, collectTrace);
  // Session time travels with the evidence so outcomes can be attributed to
  // the living SOUL generation that was active when the session happened.
  const sessionTimes = new Map(transcripts.map((t) => [String(t.id), t.mtimeMs ?? null]));
  const tally = { done: 0, ok: 0, failed: 0, skipped: 0 };
  const records = await analyzeTraces(traces, {
    invoke,
    contexts: loadContexts({ soulPath, posturePath, experiencePath }),
    stateDir,
    runId,
    jobs,
    onRecord: (record) => {
      const file = evidenceFile(stateDir, record.transcriptId);
      // A failed or skipped re-analysis never replaces earlier good evidence.
      if (record.status === "ok" || readJson(file)?.status !== "ok") {
        writeJson(file, { ...record, sessionAt: sessionTimes.get(String(record.transcriptId)) ?? null });
      }
      tally.done += 1;
      tally[record.status] += 1;
      emit("analyze:tick", { ...tally });
    },
  });
  emit("analyze:done", { ...tally });

  const evidenceRecords = readEvidenceRecords(stateDir);
  emit("fold:start");
  const consolidation = await consolidateLedger(foldEvidence(evidenceRecords, { minGapEvidence: floor }), {
    invoke,
    stateDir,
    runId,
    minGapEvidence: floor,
  });
  saveOpenGaps(stateDir, consolidation.openGaps);
  const { ledger } = consolidation;
  writeJson(path.join(stateDir, "ledger.json"), ledger);
  emit("fold:done", { clusters: ledger.clusters.length, eligible: ledger.clusters.filter((c) => c.eligible).length });

  const proposal = await propose({
    stateDir,
    runId,
    ledger,
    evidenceRecords,
    soul,
    floor,
    invoke,
    analyzer,
    consolidation,
    harnessSummary: Object.entries(perHarness).map(([h, n]) => `${h} ${n}`).join(", ") || "none",
    emit,
    stats: {
      transcripts: transcripts.length,
      analyzed: tally.ok,
      skipped: tally.skipped,
      failed: tally.failed,
    },
  });

  const processed = readSessionCheckpoint(stateDir);
  const done = new Set(records.filter((r) => r.status === "ok" || r.status === "skipped").map((r) => r.transcriptId));
  for (const t of transcripts) if (done.has(t.id)) processed[checkpointKey(t)] = t.mtimeMs ?? null;
  writeJson(path.join(stateDir, "cursor.json"), {
    version: 2,
    lastRun: proposal.createdAt,
    lastProposalId: proposal.id,
    processed,
    perHarness: discovery.perHarness,
  });
  return proposal;
}
