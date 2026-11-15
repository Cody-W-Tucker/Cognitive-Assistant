// Blind, delayed scoring. The trace is the snapshot taken when the session was
// analyzed, never the analysis itself (which contains alignment context), and
// it is used only while the session's transcript is unchanged. A session that
// cannot be scored is left without an outcome: nothing is written for it, a
// later run tries again, and verdicts ignore it.
import fs from "node:fs";
import path from "node:path";
import { createHash, randomBytes } from "node:crypto";
import { collectFollowup, touchedPaths } from "./followup.js";
import { cutoffMs, discoverTranscripts, isLangfuseRevision, readTranscript, transcriptRevision } from "./harnesses.js";
import { distill } from "./distill.js";
import { langfuseClient } from "./langfuse.js";
import { mockInvoke } from "./mock.js";
import { assertModelConfigured, modelInvoke } from "./model.js";
import { loadPrompt, renderPrompt } from "./prompts.js";
import { checkpointKey, evidenceFile, readEvidenceRecords, readJson, writeJson } from "./state.js";

/** What the runtime keeps about when and where a session happened. */
export function sessionMeta(session) {
  const startedAt = session?.startedAtMs ?? null;
  const ended = session?.mtimeMs;
  return {
    sessionAt: startedAt ?? (session?.harness === "hermes" ? null : session?.mtimeMs) ?? null,
    startedAt,
    endedAt: ended ? new Date(ended).toISOString() : null,
    source: session?.source ?? null,
    cwd: session?.cwd ?? null,
    gitRepoRoot: session?.gitRepoRoot ?? null,
    parentSessionId: session?.parentSessionId ?? null,
  };
}

/** The blind trace the outcome judge reads, tied to the transcript revision it was cut from. */
export function outcomeSnapshot(session, events, revision) {
  const said = (text) => text.split("--- Attached Context ---", 1)[0];
  return {
    revision,
    location: { harness: session.harness, id: session.id },
    trace: distill(events, session),
    texts: events.filter((e) => e.kind === "message" && ["user", "assistant"].includes(e.role) && typeof e.text === "string")
      .flatMap((e) => { const text = said(e.text).trim(); return [text.slice(0, 4800), text.slice(-1000)]; }),
    firstUserMessage: said(events.find((e) => e.kind === "message" && e.role === "user" && e.text)?.text || "").slice(0, 500),
    touched: touchedPaths(events),
  };
}

const DAY = 86400000;
const labels = new Set(["advanced", "stalled", "regressed", "answered", "unclear"]);
// A label that claims nothing about what happened next needs no citation.
const uncited = new Set(["answered", "unclear"]);
const time = (v) => v == null || v === "" ? NaN : typeof v === "number" ? v : Date.parse(v);

export function validateOutcome(reply, trace, followup, traceTexts = []) {
  if (!reply || typeof reply.aim !== "string" || !reply.aim.trim() || typeof reply.reason !== "string" || !reply.reason.trim() || !labels.has(reply.label) || !Array.isArray(reply.evidence) || (!uncited.has(reply.label) && !reply.evidence.length)) return false;
  const sources = new Map(Object.values(followup).flat().map((item) => [item.ref, [item.firstUser, item.lastAssistant, item.subject, item.text].filter((v) => typeof v === "string")]));
  return reply.evidence.every(({ ref, quote } = {}) => typeof ref === "string" && typeof quote === "string" && quote.trim() && (ref === "trace" ? trace.includes(quote) && traceTexts.some((text) => text.includes(quote)) : sources.has(ref) && sources.get(ref).some((value) => value.includes(quote))));
}

/**
 * Score matured sessions that have analysis evidence and no outcome yet.
 * `dryRun` writes a preview file instead of touching evidence, and also
 * previews finished Hermes sessions that were never analyzed, reading their
 * transcripts as they stand: that is the backtest.
 *
 * Evidence analyzed before sessions came from Langfuse carries a snapshot
 * tied to a local store revision, which can never match again. Such a
 * snapshot (or a missing one) is re-cut once from Langfuse and saved.
 */
export async function runOutcome({ client = null, stateDir, since = "all", limit = null, dryRun = false, rescore = false, matureDays = 3, analyzer = "model", invoke = null, modelName = null, now = Date.now(), collect = collectFollowup } = {}) {
  if (!stateDir) throw new Error("outcome: --state-dir is required");
  const days = Number(matureDays);
  if (matureDays === "" || !Number.isFinite(days) || days < 0) throw new Error("--mature-days must be non-negative");
  if (limit !== null && (!Number.isInteger(Number(limit)) || Number(limit) < 1)) throw new Error("--limit must be a positive integer");
  if (!["model", "mock"].includes(analyzer)) throw new Error("--analyzer must be model or mock");
  const cutoff = cutoffMs(since, now);
  const custom = Boolean(invoke);
  if (!invoke) { if (analyzer === "mock") invoke = mockInvoke; else { assertModelConfigured(); invoke = modelInvoke(stateDir); } }
  const model = modelName || (custom ? "custom" : analyzer === "mock" ? "mock" : (process.env.CA_LLM_MODEL_OUTCOME || process.env.CA_LLM_MODEL));
  const rubric = { promptSha: createHash("sha256").update(loadPrompt("outcome")).digest("hex"), model, matureDays: days };
  client ??= langfuseClient();
  // One discovery serves every lookup in this run, including follow-up.
  let pool = null;
  const discovered = async () => (pool ??= (await discoverTranscripts({ client, stateDir, since: "all", ignoreCheckpoint: true, now })).transcripts);
  const evidence = readEvidenceRecords(stateDir);
  const candidates = evidence.filter((r) => rescore || !r.outcome).map((record) => ({ record }));
  if (dryRun) {
    const analyzed = new Set(evidence.map((r) => checkpointKey({ harness: r.harness, id: r.transcriptId })));
    for (const session of await discovered()) {
      if (session.harness !== "hermes" || analyzed.has(checkpointKey(session))) continue;
      candidates.push({ record: { harness: session.harness, transcriptId: session.id, ...sessionMeta(session) }, session });
    }
  }
  const rows = candidates.filter(({ record }) => {
    const ended = time(record.endedAt);
    return Number.isFinite(ended) && ended >= cutoff && ended + days * DAY <= now;
  }).sort((a, b) => time(b.record.endedAt) - time(a.record.endedAt));
  const selected = limit === null ? rows : rows.slice(0, Number(limit));
  const runId = `outcome-${new Date(now).toISOString().replace(/[-:.TZ]/g, "")}-${randomBytes(4).toString("hex")}`;
  const preview = dryRun ? path.join(stateDir, "outcome-preview", `${runId}.jsonl`) : null;
  if (preview) { fs.mkdirSync(path.dirname(preview), { recursive: true, mode: 0o700 }); fs.writeFileSync(preview, "", { mode: 0o600 }); }
  const results = [];
  const evidencePath = (record) => {
    const qualified = evidenceFile(stateDir, record.transcriptId, record.harness);
    return readJson(qualified)?.status === "ok" ? qualified : evidenceFile(stateDir, record.transcriptId);
  };
  for (const { record: candidate, session: unanalyzed } of selected) {
    let record = candidate;
    try {
      const session = unanalyzed ?? { harness: record.harness, id: record.transcriptId };
      let snapshot = unanalyzed ? null : record.outcomeSnapshot;
      let revision = null;
      if (!isLangfuseRevision(snapshot?.revision)) {
        const read = await readTranscript(session, { client });
        if (read.self) throw new Error("the runtime's own session");
        snapshot = outcomeSnapshot(session, read.events, read.revision);
        revision = read.revision;
        if (!unanalyzed && !dryRun) {
          record = { ...record, outcomeSnapshot: snapshot };
          writeJson(evidencePath(record), record);
        }
      }
      revision ??= await transcriptRevision(session, { client });
      if (!revision || JSON.stringify(snapshot.revision) !== JSON.stringify(revision)) throw new Error("original session changed since its snapshot");
      const { trace, firstUserMessage, texts, touched } = snapshot;
      if (typeof trace !== "string" || !Array.isArray(texts)) throw new Error("invalid original session snapshot");
      const followup = await collect({ session: record, firstUserMessage, matureDays: days, client, stateDir, candidates: discovered, touched });
      if (JSON.stringify(revision) !== JSON.stringify(await transcriptRevision(session, { client }))) throw new Error("original session changed");
      const prompt = renderPrompt("outcome", { TRACE: trace, FOLLOWUP: JSON.stringify(followup, null, 2) });
      const valid = (reply) => validateOutcome(reply, trace, followup, texts);
      const reply = await invoke("outcome", prompt, { trace, followup, validate: valid });
      if (!valid(reply)) throw new Error("invalid outcome reply");
      const outcome = { aim: reply.aim, label: reply.label, reason: reply.reason, evidence: reply.evidence, rubric, scoredAt: new Date(now).toISOString() };
      if (!dryRun) writeJson(evidencePath(record), { ...record, outcome });
      const result = {
        harness: record.harness, transcriptId: record.transcriptId, source: record.source ?? null,
        startedAt: record.startedAt ?? null, endedAt: record.endedAt,
        followup: Object.fromEntries(Object.entries(followup).map(([kind, items]) => [kind, items.length])),
        outcome,
      };
      results.push(result);
      if (preview) fs.appendFileSync(preview, `${JSON.stringify(result)}\n`, { mode: 0o600 });
    } catch { /* left unscored; see the header comment */ }
  }
  return { runId, preview, selected: selected.length, scored: results.length, unscored: selected.length - results.length, results };
}
