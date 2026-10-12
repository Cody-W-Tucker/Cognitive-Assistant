// Full headless pipeline: discover -> collect -> distill -> analyze
// (acpx-only, injectable) -> fold (deterministic) -> consolidate (one
// judged acpx call, fail-soft to lexical) -> synthesize (mock deterministic
// or production acpx, fail-closed) -> proposal. Writes private state only;
// never touches the CA repo, tracked files, or live Hermes.

import fs from "node:fs";
import path from "node:path";

import { discoverTranscripts } from "./discovery.js";
import { distill, recordToEvents } from "./distill.js";
import { analyzeTraces, mockInvoke, assertAcpxAvailable } from "./analyze.js";
import { foldEvidence } from "./fold.js";
import { consolidateLedger } from "./consolidate.js";
import { synthesizeCandidates, synthesizeWithAcpx } from "./synthesize.js";
import { stageCandidates, buildFinalProposal } from "./stage.js";
import { measureStaging } from "./measure.js";
import { annotateStaging, applyRejectionSuppression, buildMockFinalAnnotation } from "./annotate.js";
import { initStateDir, writeJson } from "./state.js";

function readJsonlEvents(file) {
  const events = [];
  let text;
  try {
    text = fs.readFileSync(file, "utf8");
  } catch {
    return events;
  }
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      events.push(...recordToEvents(JSON.parse(trimmed)));
    } catch {
      // skip unparseable lines; the raw file stays referenced in the trace
    }
  }
  return events;
}

async function readSqliteMessages(dbPath, sessionId) {
  let sqlite;
  try {
    sqlite = await import("node:sqlite");
  } catch {
    return [];
  }
  const events = [];
  let db;
  try {
    db = new sqlite.DatabaseSync(dbPath, { readOnly: true });
    const tables = new Set(
      db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all().map((r) => r.name),
    );
    let rows = [];
    if (tables.has("session_message")) {
      rows = db
        .prepare("SELECT data FROM session_message WHERE session_id = ? ORDER BY seq ASC")
        .all(sessionId)
        .map((r) => r.data);
    } else if (tables.has("messages")) {
      rows = db
        .prepare("SELECT role, text FROM messages WHERE session_id = ? ORDER BY rowid ASC")
        .all(sessionId)
        .map((r) => ({ role: r.role, text: Buffer.isBuffer(r.text) ? r.text.toString("utf8") : r.text }));
    }
    for (const row of rows) {
      if (typeof row === "string") {
        try {
          events.push(...recordToEvents(JSON.parse(row)));
        } catch {
          events.push({ kind: "message", role: "user", text: row });
        }
      } else {
        events.push(...recordToEvents(row));
      }
    }
  } catch {
    // unreadable here mirrors discovery fail-soft: trace carries no events
  } finally {
    try {
      db?.close();
    } catch {
      // ignore
    }
  }
  return events;
}

async function collectTraces(transcripts) {
  const traces = [];
  for (const transcript of transcripts) {
    let events = [];
    if (transcript.path) events = readJsonlEvents(transcript.path);
    else if (transcript.db) events = await readSqliteMessages(transcript.db, transcript.id);
    traces.push({
      transcriptId: transcript.id,
      harness: transcript.harness,
      distilled: distill(events, transcript),
    });
  }
  return traces;
}

function readRejections(stateDir) {
  const out = [];
  try {
    const text = fs.readFileSync(path.join(path.resolve(stateDir), "rejections.jsonl"), "utf8");
    for (const line of text.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        out.push(JSON.parse(trimmed));
      } catch {
        // skip malformed rejection lines; the raw file stays for audit
      }
    }
  } catch {
    // no rejections yet
  }
  return out;
}

function harnessSummaryOf(transcripts) {
  const counts = new Map();
  for (const t of transcripts || []) counts.set(t.harness, (counts.get(t.harness) || 0) + 1);
  const parts = [...counts.entries()].map(([h, n]) => `${h} ${n}`);
  return parts.join(", ") || "none";
}

function readSoulBaseline(soulPath) {
  if (!soulPath) return "";
  try {
    return fs.readFileSync(soulPath, "utf8").slice(0, 4000);
  } catch {
    return "";
  }
}

/**
 * Run the headless pass. All writes land under `stateDir`.
 *
 * Injectable model invokes (no real acpx in tests): `analyzeInvoke`
 * overrides the per-trace analyzer, `consolidateInvoke` the one judged
 * consolidation call, `synthesizeInvoke` the production synthesis call.
 * Each defaults to the analyzer selection (`mock` double vs real acpx).
 *
 * @returns the proposal object (also written to stateDir/proposal.json)
 */
export async function runPipeline({
  home,
  stateDir,
  since = "30d",
  harnesses = null,
  analyzer = "acpx",
  soulPath = null,
  posturePath = null,
  experienceRoot = null,
  promptsDir = null,
  runId = null,
  minGapEvidence = 2,
  analyzeInvoke = null,
  consolidateInvoke = null,
  synthesizeInvoke = null,
  annotateInvoke = null,
} = {}) {
  initStateDir(stateDir);
  const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
  const discovery = discoverTranscripts({ home, stateDir, since, harnesses });
  const traces = await collectTraces(discovery.transcripts);
  if (analyzer !== "mock" && !analyzeInvoke) {
    // Real production run path only: fail fast before trace analysis when
    // the acpx binary selected via CA_IMPROVE_ACPX_BIN/BACKPASS_ACPX_BIN is
    // unavailable. Mock runs and injected invokes bypass real acpx entirely.
    assertAcpxAvailable();
  }
  const invoke = analyzeInvoke || (analyzer === "mock" ? mockInvoke : undefined);
  const records = analyzeTraces(traces, {
    ...(invoke ? { invoke } : {}),
    stateDir,
    runId: resolvedRun,
    soulPath,
    posturePath,
    experienceRoot,
    promptsDir,
  });
  for (const record of records) {
    writeJson(path.join(stateDir, "evidence", `${record.transcriptId}.json`), record);
  }
  const folded = foldEvidence(records, { minGapEvidence });
  // Consolidation is acpx-only when >=2 eligible gaps exist; the mock
  // analyzer keeps deterministic lexical identity with a visible note.
  const consolidation = consolidateLedger(folded, {
    ...(consolidateInvoke ? { invoke: consolidateInvoke } : analyzer === "mock" ? { analyzer: "mock" } : {}),
    stateDir,
    runId: resolvedRun,
    promptsDir,
    minGapEvidence,
  });
  const ledger = consolidation.ledger;
  writeJson(path.join(stateDir, "ledger.json"), ledger);
  const evidenceIndex = new Map(records.map((r) => [r.transcriptId, r.positive || []]));
  const soulBaseline = readSoulBaseline(soulPath);
  const rejections = readRejections(stateDir);
  const harnessSummary = harnessSummaryOf(discovery.transcripts);
  const runNote = consolidation.note || "";
  let edits;
  let synthesisNote = "";
  let synthesisFailed = false;
  if (analyzer === "mock") {
    // Deterministic reviewable path: narrow change plans only, no model
    // traffic, no real acpx calls. Final records come only from the mock
    // annotate step below (same plan->stage/measure->preface->annotate path).
    edits = synthesizeCandidates(ledger, { evidenceIndex, soulBaseline });
  } else {
    // Production acpx-only synthesis: strict validation, fail-closed.
    const out = synthesizeWithAcpx(ledger, {
      evidenceIndex,
      soulBaseline,
      rejections,
      ...(synthesizeInvoke ? { invoke: synthesizeInvoke } : {}),
      stateDir,
      runId: resolvedRun,
      promptsDir,
      transcriptCount: discovery.transcripts.length,
      harnessSummary,
      runNote,
    });
    edits = out.edits;
    synthesisFailed = Boolean(out.failed);
    synthesisNote = out.note || "";
  }
  const notes = [runNote, synthesisNote].filter(Boolean);
  // Staged change plan: synth output is never final. Stage narrow plans
  // deterministically, measure with stable change ids/deltas + provisional
  // intent/eligible context, annotate via fresh preface->annotate
  // invocations (sole full-record origin), suppress rejections on
  // annotated finals, then build the terminal proposal from annotated
  // finals only. Fail closed with no edits.
  const staged = stageCandidates(edits, { stateDir, runId: resolvedRun });
  measureStaging(staged, { stateDir, runId: resolvedRun, ledger, evidenceIndex });
  // Mock follows the same plan->private stage/measure->preface->
  // annotate-final path and may deterministically construct the equivalent
  // final annotation (mock only). Production invents nothing: without an
  // annotate invoke that supplies complete final records, annotate fails
  // closed with no edits.
  const mockFinalFor = (plans) =>
    (plans || staged).map((c) => buildMockFinalAnnotation(c, { ledger, evidenceIndex, soulBaseline }));
  const defaultAnnotate = (args) => {
    if (analyzer === "mock") {
      return { status: "ok", annotations: mockFinalFor(args?.staged || staged) };
    }
    return { status: "failed", error: "annotate invoke unavailable; production invents nothing" };
  };
  const annInvoke = annotateInvoke || defaultAnnotate;
  const annOut = await annotateStaging(staged, {
    stateDir,
    invoke: (args) => annInvoke({ ...args, staged: args?.staged || staged }),
    runId: resolvedRun,
    ledger,
    evidenceIndex,
    soulBaseline,
    ...(promptsDir ? { promptsDir } : {}),
  });
  let finalEdits = [];
  let annotateNote = "";
  let annotateFailed = false;
  if (annOut.failed) {
    annotateFailed = true;
    annotateNote = `annotate failed (${annOut.error || "invalid"}); fail-closed with no candidate edits for this run`;
  } else {
    const kept = applyRejectionSuppression(annOut.annotated || [], rejections, { evidenceIndex });
    try {
      finalEdits = buildFinalProposal(kept, { stateDir, ledger, evidenceIndex, soulBaseline });
    } catch (err) {
      annotateFailed = true;
      annotateNote = `final proposal blocked (${err?.message || err}); unannotated staging cannot reach apply`;
      finalEdits = [];
    }
  }
  if (annotateNote) notes.push(annotateNote);
  const proposal = {
    version: 1,
    id: `prop-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`,
    createdAt: new Date().toISOString(),
    reviewed: false,
    appliedAt: null,
    scope: "global",
    minGapEvidence,
    edits: finalEdits,
    notes,
    consolidation: {
      skipped: Boolean(consolidation.skipped),
      failed: Boolean(consolidation.failed),
      merged: consolidation.merged || 0,
      note: consolidation.note || "",
    },
    synthesis: {
      analyzer,
      failed: synthesisFailed,
      note: synthesisNote,
    },
    staging: {
      staged: staged.length,
      annotated: annOut.annotated ? annOut.annotated.length : 0,
      failed: annotateFailed,
      note: annotateNote,
    },
    stats: {
      transcripts: discovery.transcripts.length,
      analyzed: records.filter((r) => r.status === "ok").length,
      failed: records.filter((r) => r.status !== "ok").length,
      clusters: ledger.clusters.length,
      eligible: ledger.clusters.filter((c) => c.eligible).length,
    },
  };
  writeJson(path.join(stateDir, "proposal.json"), proposal);
  writeJson(path.join(stateDir, "cursor.json"), {
    lastRun: proposal.createdAt,
    lastProposalId: proposal.id,
    analyzedIds: records.map((r) => r.transcriptId).sort(),
    perHarness: discovery.perHarness,
  });
  return proposal;
}
