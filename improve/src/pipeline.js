// `ca-improve run`: discover -> collect -> distill -> analyze -> fold ->
// consolidate -> propose. Writes private state only; never touches the CA
// repo, tracked files, or live Hermes.

import path from "node:path";
import { createHash } from "node:crypto";

import { analyzeTraces, loadContexts } from "./analyze.js";
import { consolidateLedger, saveOpenGaps } from "./consolidate.js";
import { distill } from "./distill.js";
import { foldEvidence } from "./fold.js";
import { discoverTranscripts, readTranscript, SUPPORTED_HARNESSES } from "./harnesses.js";
import { langfuseClient } from "./langfuse.js";
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

/**
 * An unreadable session becomes a failed trace, retried next run rather than
 * checkpointed. The runtime's own sessions are skipped (and checkpointed).
 */
async function collectTrace(transcript, client) {
  let events, revision, self;
  try {
    ({ events, revision, self } = await readTranscript(transcript, { client }));
  } catch (err) {
    return { transcriptId: transcript.id, harness: transcript.harness, readError: `unreadable session: ${err.message}` };
  }
  if (self) return { transcriptId: transcript.id, harness: transcript.harness, skipReason: "the runtime's own session" };
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
    // Cut from the same observations as the trace; scoring later checks the session is unchanged.
    outcomeSnapshot: revision ? outcomeSnapshot(transcript, events, revision) : null,
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

/** Langfuse records no session end: a session is finished once it has been idle long enough. */
export function sessionEligible(transcript, now, idleHours) {
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
  client = null,
  stateDir,
  soulPath,
  posturePath = null,
  experiencePath = null,
  since = "30d",
  harnesses = null,
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
  client ??= langfuseClient();
  initStateDir(stateDir);
  const runId = timestampId("run");

  emit("discover:start", { harnesses: harnesses || SUPPORTED_HARNESSES });
  const needsMetadata = (t) => {
    if (t.harness !== "hermes") return false;
    const evidence = readSessionEvidence(stateDir, t.harness, t.id);
    return evidence?.status === "ok" && (evidence.startedAt == null || evidence.source == null);
  };
  const now = Date.now();
  const discovery = await discoverTranscripts({ client, stateDir, since, harnesses, idleHours: Number(idleHours), now, includeCheckpointed: needsMetadata });
  for (const t of discovery.transcripts) {
    if (!needsMetadata(t) || t.startedAtMs == null || !t.source) continue;
    const evidence = readSessionEvidence(stateDir, t.harness, t.id);
    if (evidence.source != null && evidence.source !== t.source) continue;
    // No new rubric: the analysis was made under the original, possibly unknown one.
    writeJson(evidenceFile(stateDir, t.id, t.harness), {
      ...evidence, sessionAt: evidence.startedAt ?? t.startedAtMs, startedAt: evidence.startedAt ?? t.startedAtMs,
      source: t.source, endedAt: evidence.endedAt ?? sessionMeta(t).endedAt, cwd: evidence.cwd ?? t.cwd,
      gitRepoRoot: evidence.gitRepoRoot ?? null, parentSessionId: evidence.parentSessionId ?? null,
    });
  }
  // Sessions already analyzed (say, under an older checkpoint value) are re-checkpointed, never re-analyzed.
  const analyzed = discovery.transcripts.filter((t) => readSessionEvidence(stateDir, t.harness, t.id)?.status === "ok");
  const eligible = discovery.transcripts.filter((t) => !analyzed.includes(t) && sessionEligible(t, now, Number(idleHours)));
  const transcripts = capSessions(eligible, cap);
  const perHarness = countByHarness(transcripts);
  emit("discover:done", { transcripts: transcripts.length, perHarness });

  emit("analyze:start", { total: transcripts.length, pending: transcripts.length, analyzer });
  const traces = await mapPool(transcripts, jobs, (t) => collectTrace(t, client));
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
  await runOutcome({ client, stateDir, since: "all", limit: cap, analyzer, invoke, modelName: customInvoke ? "custom" : analyzer === "mock" ? "mock" : (process.env.CA_LLM_MODEL_OUTCOME || process.env.CA_LLM_MODEL) });
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
  for (const t of analyzed) processed[checkpointKey(t)] = t.mtimeMs ?? null;
  writeJson(path.join(stateDir, "cursor.json"), {
    version: 2,
    lastRun: proposal.createdAt,
    lastProposalId: proposal.id,
    processed,
    perHarness: discovery.perHarness,
  });
  return proposal;
}
