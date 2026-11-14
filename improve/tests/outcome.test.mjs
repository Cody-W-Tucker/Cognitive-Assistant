import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { runOutcome, validateOutcome } from "../src/outcome.js";
import { evidenceFile, writeJson } from "../src/state.js";
import { transcriptRevision } from "../src/harnesses.js";

const followup = { sessions: [{ ref: "session:later", firstUser: "Still stuck" }], commits: [], journal: [] };
const reply = { aim: "Fix the bug", label: "stalled", reason: "It remains", evidence: [{ ref: "trace", quote: "Fix the bug" }] };
test("validates citations and verbatim quotes", () => {
  assert.ok(validateOutcome(reply, "Fix the bug", followup, ["Fix the bug"]));
  assert.ok(!validateOutcome({ ...reply, evidence: [{ ref: "session:other", quote: "Still stuck" }] }, "Fix the bug", followup));
  assert.ok(!validateOutcome({ ...reply, evidence: [{ ref: "trace", quote: "invented" }] }, "Fix the bug", followup));
  assert.ok(!validateOutcome({ ...reply, evidence: [{ ref: "session:later", quote: "invented" }] }, "Fix the bug", followup));
  assert.ok(!validateOutcome({ ...reply, evidence: [{ ref: "session:later", quote: "session:later" }] }, "Fix the bug", followup));
  assert.ok(!validateOutcome(reply, "Fix the bug", followup, []));
});
test("CLI leaves an unscorable session alone without failing or printing private evidence", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "outcome-cli-"));
  writeJson(evidenceFile(dir, "x", "claude"), { harness: "claude", transcriptId: "x", status: "ok", endedAt: "2020-01-01T00:00:00Z", outcomeSnapshot: { trace: "PRIVATE QUOTE" } });
  const result = spawnSync(process.execPath, ["bin/ca-improve.js", "outcome", "--state-dir", dir, "--analyzer", "mock"], { cwd: path.resolve("."), encoding: "utf8" });
  assert.equal(result.status, 0);
  assert.equal(JSON.parse(result.stdout).unscored, 1);
  assert.doesNotMatch(result.stdout + result.stderr, /PRIVATE QUOTE/);
  assert.deepEqual(fs.readdirSync(dir), ["evidence"]);
});
test("maturation, preview, unscored sessions, and explicit rescore", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "outcome-test-"));
  const transcript = path.join(dir, "trace.jsonl");
  fs.writeFileSync(transcript, JSON.stringify({ type: "user", message: { role: "user", content: "Fix the bug" } }) + "\n");
  const record = { harness: "claude", transcriptId: "x", status: "ok", source: null, startedAt: 5, endedAt: "2026-01-01T00:00:00Z", positive: [1], negative: [], gaps: [], outcomeSnapshot: { revision: transcriptRevision({ harness: "claude", path: transcript }), trace: "Fix the bug", texts: ["Fix the bug"], firstUserMessage: "Fix the bug" } };
  const file = evidenceFile(dir, "x", "claude");
  writeJson(file, record);
  const options = { stateDir: dir, now: Date.parse("2026-01-04T00:00:00Z"), transcripts: [{ harness: "claude", id: "x", path: transcript }], collect: async () => followup, invoke: async (_role, prompt) => { assert.ok(!prompt.includes("SOUL_BASELINE")); return reply; } };
  const before = fs.readFileSync(file, "utf8");
  const preview = await runOutcome({ ...options, dryRun: true });
  assert.equal(preview.scored, 1);
  assert.equal(fs.readFileSync(file, "utf8"), before);
  const row = JSON.parse(fs.readFileSync(preview.preview, "utf8"));
  assert.equal(row.outcome.label, "stalled");
  assert.deepEqual([row.source, row.startedAt, row.endedAt, row.followup], [null, 5, record.endedAt, { sessions: 1, commits: 0, journal: 0 }]);
  assert.equal((await runOutcome({ ...options, now: options.now - 1 })).selected, 0);
  assert.equal((await runOutcome({ ...options, invoke: async () => ({ ...reply, evidence: [] }) })).unscored, 1);
  assert.equal(fs.readFileSync(file, "utf8"), before);
  assert.equal((await runOutcome(options)).scored, 1);
  assert.equal(JSON.parse(fs.readFileSync(file)).outcome.rubric.matureDays, 3);
  assert.deepEqual(JSON.parse(fs.readFileSync(file)).positive, [1]);
  assert.equal((await runOutcome(options)).selected, 0);
  assert.equal((await runOutcome({ ...options, rescore: true })).scored, 1);
  fs.appendFileSync(transcript, "changed");
  assert.equal((await runOutcome({ ...options, rescore: true })).unscored, 1);
  assert.deepEqual(fs.readdirSync(dir).sort(), ["evidence", "outcome-preview", "trace.jsonl"]);
});

function hermesStore(dir, sessions) {
  const dbPath = path.join(dir, ".hermes", "state.db");
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const db = new DatabaseSync(dbPath);
  db.exec("CREATE TABLE sessions (id TEXT, source TEXT, started_at REAL, last_activity_at REAL, ended_at REAL, end_reason TEXT); CREATE TABLE messages (session_id TEXT, role TEXT, content TEXT)");
  for (const [id, source, started, active, ended] of sessions) {
    db.prepare("INSERT INTO sessions VALUES (?, ?, ?, ?, ?, NULL)").run(id, source, started / 1000, active / 1000, ended === null ? null : ended / 1000);
    db.prepare("INSERT INTO messages VALUES (?, 'user', 'Fix the bug')").run(id);
  }
  db.close();
  return dbPath;
}

test("a dry run previews finished Hermes sessions that were never analyzed", async () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "outcome-backtest-"));
  const dir = path.join(home, "state"), end = Date.parse("2026-01-01T00:00:00Z"), now = end + 10 * 86400000;
  hermesStore(home, [
    // Reaped a week after the person stopped: last activity is the end.
    ["reaped", "desktop", end - 3600000, end, end + 7 * 86400000],
    ["cron", "cron", end - 3600000, end, end],
    ["fresh", "desktop", now - 3600000, now - 1800000, now - 1800000],
  ]);
  const seen = [];
  const options = { home, stateDir: dir, now, invoke: async () => reply, collect: async ({ session, candidates }) => { seen.push([session.transcriptId, session.endedAt, candidates().length]); return followup; } };
  assert.equal((await runOutcome(options)).selected, 0);
  const preview = await runOutcome({ ...options, dryRun: true });
  assert.deepEqual([preview.selected, preview.scored, preview.unscored], [2, 2, 0]);
  assert.deepEqual(seen.map(([id, ended]) => [id, ended]).sort(), [["cron", new Date(end).toISOString()], ["reaped", new Date(end).toISOString()]]);
  assert.ok(seen.every(([, , count]) => count === 3));
  const rows = fs.readFileSync(preview.preview, "utf8").trim().split("\n").map((line) => JSON.parse(line));
  assert.deepEqual(rows.map((row) => row.source).sort(), ["cron", "desktop"]);
  assert.ok(!fs.existsSync(path.join(dir, "evidence")));
});

test("reaping a Hermes session after analysis does not make it unscorable; new messages do", async () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "outcome-reap-"));
  const end = Date.parse("2026-01-01T00:00:00Z");
  const dbPath = hermesStore(home, [["x", "desktop", end - 3600000, end, null]]);
  const session = { harness: "hermes", id: "x", db: dbPath };
  const evidence = evidenceFile(home, "x", "hermes");
  writeJson(evidence, { harness: "hermes", transcriptId: "x", status: "ok", endedAt: new Date(end).toISOString(), outcomeSnapshot: { location: session, revision: transcriptRevision(session), trace: "Fix the bug", texts: ["Fix the bug"] } });
  const options = { stateDir: home, now: end + 4 * 86400000, collect: async () => followup, invoke: async () => reply, rescore: true };
  const db = new DatabaseSync(dbPath);
  db.exec("UPDATE sessions SET ended_at = 9999999999, end_reason = 'startup_orphan_reap'");
  assert.equal((await runOutcome(options)).scored, 1);
  db.exec("INSERT INTO messages VALUES ('x', 'user', 'reopened')");
  db.close();
  assert.deepEqual([(await runOutcome(options)).scored, (await runOutcome(options)).unscored], [0, 1]);
});
