import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { discoverTranscripts } from "./discovery.js";
import { runPipeline } from "./pipeline.js";

function tmpRoot() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "hermes-"));
}

async function makeHermesDb(dbPath, { sessionsDdl, messagesDdl, sessions = [], messages = [] }) {
  const sqlite = await import("node:sqlite");
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  try { fs.unlinkSync(dbPath); } catch {}
  const db = new sqlite.DatabaseSync(dbPath);
  db.exec(sessionsDdl);
  if (messagesDdl) db.exec(messagesDdl);
  for (const s of sessions) {
    const cols = Object.keys(s);
    const placeholders = cols.map(() => "?").join(", ");
    db.prepare(`INSERT INTO sessions (${cols.join(", ")}) VALUES (${placeholders})`).run(...cols.map((c) => s[c]));
  }
  for (const m of messages) {
    const cols = Object.keys(m);
    const placeholders = cols.map(() => "?").join(", ");
    db.prepare(`INSERT INTO messages (${cols.join(", ")}) VALUES (${placeholders})`).run(...cols.map((c) => m[c]));
  }
  db.close();
}

const nowSec = () => Math.floor(Date.now() / 1000);
const daysAgoSec = (d) => nowSec() - d * 86400;

const CURRENT_SESSIONS_DDL = `CREATE TABLE sessions (id TEXT PRIMARY KEY, started_at INTEGER, last_activity_at INTEGER, cwd TEXT)`;
const CURRENT_MESSAGES_DDL = `CREATE TABLE messages (id TEXT PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, timestamp INTEGER)`;

test("current schema: cutoff keeps recent, drops stale via last_activity_at", async () => {
  const home = tmpRoot();
  const stateDir = path.join(tmpRoot(), "state");
  const dbPath = path.join(home, ".hermes", "state.db");
  await makeHermesDb(dbPath, {
    sessionsDdl: CURRENT_SESSIONS_DDL,
    messagesDdl: CURRENT_MESSAGES_DDL,
    sessions: [
      { id: "recent", started_at: daysAgoSec(29), last_activity_at: daysAgoSec(1), cwd: "/tmp" },
      { id: "stale", started_at: daysAgoSec(90), last_activity_at: daysAgoSec(60), cwd: "/tmp" },
    ],
  });
  const { transcripts } = discoverTranscripts({ home, stateDir, since: "30d", harnesses: ["hermes"] });
  const ids = transcripts.map((t) => t.id);
  assert.ok(ids.includes("recent"), `recent kept, got ${ids}`);
  assert.ok(!ids.includes("stale"), `stale dropped by cutoff, got ${ids}`);
});

test("current schema: started_at fallback when last_activity_at null", async () => {
  const home = tmpRoot();
  const stateDir = path.join(tmpRoot(), "state");
  const dbPath = path.join(home, ".hermes", "state.db");
  await makeHermesDb(dbPath, {
    sessionsDdl: CURRENT_SESSIONS_DDL,
    messagesDdl: CURRENT_MESSAGES_DDL,
    sessions: [
      { id: "started-only", started_at: daysAgoSec(1), last_activity_at: null, cwd: "/tmp" },
      { id: "started-stale", started_at: daysAgoSec(60), last_activity_at: null, cwd: "/tmp" },
    ],
  });
  const { transcripts } = discoverTranscripts({ home, stateDir, since: "30d", harnesses: ["hermes"] });
  const ids = transcripts.map((t) => t.id);
  assert.ok(ids.includes("started-only"), `started_at fallback keeps recent, got ${ids}`);
  assert.ok(!ids.includes("started-stale"), `started_at fallback drops stale, got ${ids}`);
});

test("current schema: messages.content reaches pipeline (role preserved, no text column)", async () => {
  const home = tmpRoot();
  const stateDir = path.join(tmpRoot(), "state");
  const dbPath = path.join(home, ".hermes", "state.db");
  const marker = `hermes-content-marker-${Date.now()}`;
  await makeHermesDb(dbPath, {
    sessionsDdl: CURRENT_SESSIONS_DDL,
    messagesDdl: CURRENT_MESSAGES_DDL,
    sessions: [{ id: "s1", started_at: daysAgoSec(1), last_activity_at: daysAgoSec(1), cwd: "/tmp" }],
    messages: [
      { id: "m1", session_id: "s1", role: "user", content: marker, timestamp: daysAgoSec(1) },
      { id: "m2", session_id: "s1", role: "assistant", content: "reply here", timestamp: daysAgoSec(1) },
    ],
  });
  // Discovery must not SELECT a nonexistent messages.text field.
  const disc = discoverTranscripts({ home, stateDir, since: "30d", harnesses: ["hermes"] });
  assert.ok(disc.transcripts.some((t) => t.id === "s1"), "s1 discovered without messages.text");
  // Full pipeline with injected analyzer must carry content into the distilled trace.
  let distilled = "";
  await runPipeline({
    home, stateDir, since: "30d", harnesses: ["hermes"], analyzer: "mock",
    analyzeInvoke: (args) => {
      distilled = String(args?.trace?.distilled || "");
      return { transcriptId: "s1", status: "ok", positive: [], negative: [], gaps: [] };
    },
  });
  assert.ok(distilled.includes(marker), "message content reaches distilled trace");
  assert.ok(distilled.includes("human"), "role preserved into distilled trace");
});

test("fallbacks: timestamp-less sessions use cursor, not cutoff; legacy text schema still works", async () => {
  const home = tmpRoot();
  const stateDir = path.join(tmpRoot(), "state");
  const dbPath = path.join(home, ".hermes", "state.db");
  // No temporal columns at all: cutoff must not filter, cursor owns freshness.
  await makeHermesDb(dbPath, {
    sessionsDdl: `CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT)`,
    messagesDdl: CURRENT_MESSAGES_DDL,
    sessions: [{ id: "notemporal", cwd: "/tmp" }],
  });
  let found = discoverTranscripts({ home, stateDir, since: "30d", harnesses: ["hermes"] });
  assert.ok(found.transcripts.some((t) => t.id === "notemporal"), "timestamp-less row survives cutoff via cursor fallback");
  // Legacy messages.text schema still discovered (prefers text when present).
  await makeHermesDb(dbPath, {
    sessionsDdl: CURRENT_SESSIONS_DDL,
    messagesDdl: `CREATE TABLE messages (id TEXT PRIMARY KEY, session_id TEXT, role TEXT, text TEXT)`,
    sessions: [{ id: "legacy", started_at: daysAgoSec(1), last_activity_at: daysAgoSec(1), cwd: "/tmp" }],
    messages: [{ id: "m1", session_id: "legacy", role: "user", text: "legacy hello" }],
  });
  found = discoverTranscripts({ home, stateDir, since: "30d", harnesses: ["hermes"] });
  assert.ok(found.transcripts.some((t) => t.id === "legacy"), "legacy text schema still discovered");
});

test("opencode path unchanged: missing store stays fail-soft", async () => {
  const home = tmpRoot();
  const stateDir = path.join(tmpRoot(), "state");
  const { transcripts, perHarness } = discoverTranscripts({ home, stateDir, since: "30d", harnesses: ["opencode"] });
  assert.equal(transcripts.length, 0);
  assert.equal(perHarness.opencode.error, "store missing");
});
