// Full headless pipeline: discover -> collect -> distill -> analyze
// (acpx-only, injectable) -> fold -> synthesize (candidate experience
// records) -> proposal. Writes private state only; never touches the CA
// repo, tracked files, or live Hermes.

import fs from "node:fs";
import path from "node:path";

import { discoverTranscripts } from "./discovery.js";
import { distill, recordToEvents } from "./distill.js";
import { analyzeTraces, mockInvoke } from "./analyze.js";
import { foldEvidence } from "./fold.js";
import { synthesizeCandidates } from "./synthesize.js";
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
} = {}) {
  initStateDir(stateDir);
  const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
  const discovery = discoverTranscripts({ home, stateDir, since, harnesses });
  const traces = await collectTraces(discovery.transcripts);
  const invoke = analyzer === "mock" ? mockInvoke : undefined;
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
  const ledger = foldEvidence(records, { minGapEvidence });
  writeJson(path.join(stateDir, "ledger.json"), ledger);
  const evidenceIndex = new Map(records.map((r) => [r.transcriptId, r.positive || []]));
  const soulBaseline = readSoulBaseline(soulPath);
  const edits = synthesizeCandidates(ledger, { evidenceIndex, soulBaseline });
  const proposal = {
    version: 1,
    id: `prop-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`,
    createdAt: new Date().toISOString(),
    reviewed: false,
    appliedAt: null,
    scope: "global",
    minGapEvidence,
    edits,
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
