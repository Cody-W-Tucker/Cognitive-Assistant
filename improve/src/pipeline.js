// `ca-improve run`: discover -> collect -> distill -> analyze -> fold ->
// consolidate -> propose. Writes private state only; never touches the CA
// repo, tracked files, or live Hermes.

import path from "node:path";
import { createHash } from "node:crypto";

import { analyzeTraces, loadContexts } from "./analyze.js";
import { consolidateLedger, saveOpenGaps } from "./consolidate.js";
import { distill } from "./distill.js";
import { foldEvidence } from "./fold.js";
import { discoverTranscripts, readTranscriptEvents, transcriptRevision, SUPPORTED_HARNESSES } from "./harnesses.js";
import { mockInvoke } from "./mock.js";
import { assertModelConfigured, modelInvoke } from "./model.js";
import { outcomeSnapshot, runOutcome, sessionMeta } from "./outcome.js";
import { loadPrompt } from "./prompts.js";
import { propose } from "./propose.js";
import { readSoulSnapshot } from "./soul.js";
import {
  assertMinGapEvidence,
  checkpointKey,
  evidenceFile,
  initStateDir,
  readEvidenceRecords,
  readSessionCheckpoint,
  readSessionEvidence,
  timestampId,
  writeJson,
} from "./state.js";

/** An unreadable session becomes a failed trace, retried next run rather than checkpointed. */
async function collectTrace(transcript) {
  let events;
  const revision = transcriptRevision(transcript);
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
    outcomeSnapshot: revision && (transcript.endedAt || transcript.activityKnown) && JSON.stringify(revision) === JSON.stringify(transcript.discoveryRevision) && JSON.stringify(revision) === JSON.stringify(transcriptRevision(transcript))
      ? outcomeSnapshot(transcript, events, revision) : null,
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

/**
 * Bound one run's analysis work. Hermes sessions go first because the
 * autonomous verdict is judged on them alone; within each group the newest
 * win. Checkpoints let later runs advance through the rest.
 */
export function capSessions(transcripts, max) {
  if (max == null || transcripts.length <= max) return transcripts;
  const rank = (t) => (t.harness === "hermes" ? 0 : 1);
  return [...transcripts].sort((a, b) => rank(a) - rank(b) || (b.mtimeMs || 0) - (a.mtimeMs || 0)).slice(0, max);
}

function countByHarness(transcripts) {
  const counts = {};
  for (const t of transcripts) counts[t.harness] = (counts[t.harness] || 0) + 1;
  return counts;
}

export function sessionEligible(transcript, now, idleHours) {
  if (transcript.harness !== "hermes" || transcript.endedAt != null) return true;
  return Number.isFinite(transcript.mtimeMs) && now - transcript.mtimeMs > idleHours * 3600000;
}

export function stampEvidence(record, session, rubric) {
  return { ...record, ...sessionMeta(session), rubric };
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
  idleHours = 12,
  maxSessions = null,
}) {
  const emit = (event, data = {}) => progress?.(event, data);
  const floor = assertMinGapEvidence(minGapEvidence, "minGapEvidence");
  if (!stateDir) throw new Error("improve-run: --state-dir is required");
  if (analyzer !== "model" && analyzer !== "mock") throw new Error(`improve-run: --analyzer must be model or mock (got ${JSON.stringify(analyzer)})`);
  if (maxSessions !== null && !(Number.isInteger(Number(maxSessions)) && Number(maxSessions) > 0)) throw new Error("--max-sessions must be a positive integer");
  const cap = maxSessions === null ? null : Number(maxSessions);
  if (idleHours === null || String(idleHours).trim() === "" || !Number.isFinite(Number(idleHours)) || Number(idleHours) < 0) throw new Error("--idle-hours must be a non-negative number");
  const soul = readSoulSnapshot(soulPath);
  const customInvoke = Boolean(invoke);
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
  const needsMetadata = (t) => {
    if (t.harness !== "hermes") return false;
    const evidence = readSessionEvidence(stateDir, t.harness, t.id);
    return evidence?.status === "ok" && (evidence.startedAt == null || evidence.source == null);
  };
  const now = Date.now();
  const discovery = discoverTranscripts({ home, stateDir, since, harnesses, strict: strictHarnesses, idleHours: Number(idleHours), now, includeCheckpointed: needsMetadata });
  for (const t of discovery.transcripts) {
    if (!needsMetadata(t) || t.startedAtMs == null || !t.source) continue;
    const evidence = readSessionEvidence(stateDir, t.harness, t.id);
    if (evidence.source != null && evidence.source !== t.source) continue;
    // No new rubric: the analysis was made under the original, possibly unknown one.
    writeJson(evidenceFile(stateDir, t.id, t.harness), {
      ...evidence, sessionAt: evidence.startedAt ?? t.startedAtMs, startedAt: evidence.startedAt ?? t.startedAtMs,
      source: t.source, endedAt: t.endedAt, cwd: t.cwd,
      gitRepoRoot: t.gitRepoRoot, parentSessionId: t.parentSessionId,
    });
  }
  const eligible = discovery.transcripts.filter((t) => {
    if (readSessionEvidence(stateDir, t.harness, t.id)?.status === "ok") return false;
    return sessionEligible(t, now, Number(idleHours));
  });
  const transcripts = capSessions(capOpencode(eligible, Number(process.env.CA_IMPROVE_MAX_OPENCODE_EXPORTS || 50)), cap);
  const perHarness = countByHarness(transcripts);
  emit("discover:done", { transcripts: transcripts.length, perHarness });

  emit("analyze:start", { total: transcripts.length, pending: transcripts.length, analyzer });
  const traces = await mapPool(transcripts, jobs, collectTrace);
  // Session time travels with the evidence so outcomes can be attributed to
  // the living SOUL generation that was active when the session happened.
  const sessions = new Map(transcripts.map((t) => [checkpointKey(t), t]));
  const contexts = loadContexts({ soulPath, posturePath, experiencePath });
  const sha = (value) => createHash("sha256").update(value).digest("hex");
  const rubric = {
    promptSha: sha(loadPrompt("analysis")),
    contextSha: sha(JSON.stringify([contexts.soulBaseline, contexts.interactionPosture, contexts.experienceRecords])),
    model: customInvoke ? "custom" : analyzer === "mock" ? "mock" : (process.env.CA_LLM_MODEL_ANALYSIS || process.env.CA_LLM_MODEL || null),
  };
  const tally = { done: 0, ok: 0, failed: 0, skipped: 0 };
  const records = await analyzeTraces(traces, {
    invoke,
    contexts,
    stateDir,
    runId,
    jobs,
    onRecord: (record) => {
      const file = evidenceFile(stateDir, record.transcriptId, record.harness);
      const session = sessions.get(checkpointKey({ harness: record.harness, id: record.transcriptId }));
      // A failed or skipped re-analysis never replaces earlier good evidence.
      if (record.status === "ok" || readSessionEvidence(stateDir, record.harness, record.transcriptId)?.status !== "ok") {
        const snapshot = traces.find((t) => t.harness === record.harness && t.transcriptId === record.transcriptId)?.outcomeSnapshot;
        writeJson(file, { ...stampEvidence(record, session, rubric), outcomeSnapshot: snapshot ?? null });
      }
      tally.done += 1;
      tally[record.status] += 1;
      emit("analyze:tick", { ...tally });
    },
  });
  emit("analyze:done", { ...tally });

  // Sessions that cannot be scored yet stay without an outcome and never stop the run.
  await runOutcome({ home, stateDir, since: "all", limit: cap, analyzer, invoke, modelName: customInvoke ? "custom" : analyzer === "mock" ? "mock" : (process.env.CA_LLM_MODEL_OUTCOME || process.env.CA_LLM_MODEL) });
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
  const done = new Set(records.filter((r) => r.status === "ok" || r.status === "skipped").map((r) => checkpointKey({ harness: r.harness, id: r.transcriptId })));
  for (const t of transcripts) if (done.has(checkpointKey(t))) processed[checkpointKey(t)] = t.mtimeMs ?? null;
  writeJson(path.join(stateDir, "cursor.json"), {
    version: 2,
    lastRun: proposal.createdAt,
    lastProposalId: proposal.id,
    processed,
    perHarness: discovery.perHarness,
  });
  return proposal;
}
