// Blind, delayed scoring of existing evidence. The trace is rediscovered, never
// reconstructed from the analysis (which contains alignment context).
import fs from "node:fs";
import path from "node:path";
import { createHash, randomBytes } from "node:crypto";
import { collectFollowup } from "./followup.js";
import { cutoffMs, discoverTranscripts, legacySqliteRevision, readTranscriptEvents, transcriptRevision } from "./harnesses.js";
import { distill } from "./distill.js";
import { mockInvoke } from "./mock.js";
import { assertModelConfigured, modelInvoke } from "./model.js";
import { loadPrompt, renderPrompt } from "./prompts.js";
import { checkpointKey, evidenceFile, readEvidenceRecords, readJson, writeJson } from "./state.js";

const DAY = 86400000;
const labels = new Set(["advanced", "stalled", "regressed", "unclear"]);
const time = (v) => v == null || v === "" ? NaN : typeof v === "number" ? v : Date.parse(v);

export function validateOutcome(reply, trace, followup, traceTexts = []) {
  if (!reply || typeof reply.aim !== "string" || !reply.aim.trim() || typeof reply.reason !== "string" || !reply.reason.trim() || !labels.has(reply.label) || !Array.isArray(reply.evidence) || (reply.label !== "unclear" && !reply.evidence.length)) return false;
  const sources = new Map(Object.values(followup).flat().map((item) => [item.ref, [item.firstUser, item.lastAssistant, item.subject, item.text].filter((v) => typeof v === "string")]));
  return reply.evidence.every(({ ref, quote } = {}) => typeof ref === "string" && typeof quote === "string" && quote.trim() && (ref === "trace" ? trace.includes(quote) && traceTexts.some((text) => text.includes(quote)) : sources.has(ref) && sources.get(ref).some((value) => value.includes(quote))));
}

export async function runOutcome({ home, stateDir, since = "all", limit = null, dryRun = false, rescore = false, backfillSnapshots = false, matureDays = 3, analyzer = "model", invoke = null, modelName = null, now = Date.now(), collect = collectFollowup, transcripts = null } = {}) {
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
  const rows = readEvidenceRecords(stateDir).filter((r) => {
    const ended = time(r.endedAt);
    return Number.isFinite(ended) && ended >= cutoff && ended + days * DAY <= now && (rescore || !r.outcome);
  }).sort((a, b) => time(b.endedAt) - time(a.endedAt));
  const selected = limit === null ? rows : rows.slice(0, Number(limit));
  const discovered = backfillSnapshots && selected.some((r) => !r.outcomeSnapshot && r.originalRevision)
    ? (transcripts ?? discoverTranscripts({ home, stateDir, since: "all", ignoreCheckpoint: true }).transcripts) : [];
  const runId = `outcome-${new Date(now).toISOString().replace(/[-:.TZ]/g, "")}-${randomBytes(4).toString("hex")}`;
  const preview = dryRun ? path.join(stateDir, "outcome-preview", `${runId}.jsonl`) : null;
  if (preview) { fs.mkdirSync(path.dirname(preview), { recursive: true, mode: 0o700 }); fs.writeFileSync(preview, "", { mode: 0o600 }); }
  const results = [];
  for (const record of selected) {
    let result;
    try {
      let snapshot = record.outcomeSnapshot;
      const session = snapshot?.location ? { ...snapshot.location, id: record.transcriptId } : (transcripts ?? discovered)?.find((t) => checkpointKey(t) === checkpointKey({ harness: record.harness, id: record.transcriptId }));
      if (!session || session.harness !== record.harness) throw new Error("original session unavailable");
      const revision = transcriptRevision(session);
      if (backfillSnapshots && snapshot && Array.isArray(snapshot.revision) && session.db && revision) {
        const legacy = legacySqliteRevision(session);
        if (legacy && JSON.stringify(legacy) === JSON.stringify(snapshot.revision) && JSON.stringify(revision) === JSON.stringify(transcriptRevision(session)) && JSON.stringify(legacy) === JSON.stringify(legacySqliteRevision(session))) {
          snapshot = { ...snapshot, location: session, revision };
        }
      }
      // Only an independently saved, contemporaneous revision can justify a
      // historical reconstruction. Timestamps/checkpoints alone are not proof.
      const sessionEnd = Math.max(time(session.endedAt) || 0, session.activityKnown ? time(session.mtimeMs) || 0 : 0);
      if (!snapshot && backfillSnapshots && record.originalRevision && revision && sessionEnd === time(record.endedAt) && JSON.stringify(session.discoveryRevision) === JSON.stringify(revision) && JSON.stringify(record.originalRevision) === JSON.stringify(revision)) {
        const events = await readTranscriptEvents(session);
        if (JSON.stringify(revision) !== JSON.stringify(transcriptRevision(session))) throw new Error("original session changed");
        snapshot = { revision, location: { harness: session.harness, id: session.id, path: session.path, db: session.db }, trace: distill(events, session),
          texts: events.filter((e) => e.kind === "message" && ["user", "assistant"].includes(e.role) && typeof e.text === "string").flatMap((e) => { const text = e.text.split("--- Attached Context ---", 1)[0].trim(); return [text.slice(0, 4800), text.slice(-1000)]; }),
          firstUserMessage: (events.find((e) => e.kind === "message" && e.role === "user" && e.text)?.text || "").split("--- Attached Context ---", 1)[0].slice(0, 500) };
      }
      if (!snapshot?.revision || !revision || JSON.stringify(snapshot.revision) !== JSON.stringify(revision)) throw new Error("original session snapshot unavailable or changed");
      const { trace, firstUserMessage, texts } = snapshot;
      if (typeof trace !== "string" || !Array.isArray(texts)) throw new Error("invalid original session snapshot");
      const followup = await collect({ session: record, firstUserMessage, matureDays: days, home, stateDir, originalLocation: session });
      if (JSON.stringify(revision) !== JSON.stringify(transcriptRevision(session))) throw new Error("original session changed");
      const prompt = renderPrompt("outcome", { TRACE: trace, FOLLOWUP: JSON.stringify(followup, null, 2) });
      const valid = (reply) => validateOutcome(reply, trace, followup, texts);
      const reply = await invoke("outcome", prompt, { trace, followup, validate: valid });
      if (!valid(reply)) throw new Error("invalid outcome reply");
      const outcome = { aim: reply.aim, label: reply.label, reason: reply.reason, evidence: reply.evidence, rubric, scoredAt: new Date(now).toISOString() };
      result = { harness: record.harness, transcriptId: record.transcriptId, status: "ok", outcome };
      if (!dryRun) {
        const qualified = evidenceFile(stateDir, record.transcriptId, record.harness);
        const file = readJson(qualified)?.status === "ok" ? qualified : evidenceFile(stateDir, record.transcriptId);
        writeJson(file, { ...record, outcomeSnapshot: snapshot, outcome });
      }
    } catch { result = { harness: record.harness, transcriptId: record.transcriptId, status: "failed", error: "outcome scoring failed" }; }
    results.push(result);
    if (!dryRun && result.status === "failed") {
      const failures = path.join(stateDir, "outcome-failures.jsonl");
      fs.mkdirSync(stateDir, { recursive: true, mode: 0o700 });
      fs.appendFileSync(failures, `${JSON.stringify({ ...result, runId })}\n`, { mode: 0o600 });
    }
    if (preview) fs.appendFileSync(preview, `${JSON.stringify(result)}\n`, { mode: 0o600 });
  }
  return { runId, preview, selected: selected.length, scored: results.filter((r) => r.status === "ok").length, failed: results.filter((r) => r.status === "failed").length, results };
}
