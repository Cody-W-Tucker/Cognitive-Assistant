import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { outcomeSnapshot, runOutcome, validateOutcome } from "../src/outcome.js";
import { evidenceFile, readJson, writeJson } from "../src/state.js";
import { readTranscript } from "../src/harnesses.js";
import { fakeLangfuse } from "./fake-langfuse.mjs";

const execFileAsync = promisify(execFile);
const DAY = 86400000;
const followup = { sessions: [{ ref: "session:later", firstUser: "Still stuck" }], commits: [], journal: [] };
const reply = { aim: "Fix the bug", label: "stalled", reason: "It remains", evidence: [{ ref: "trace", quote: "Fix the bug" }] };
const tmp = (prefix) => fs.mkdtempSync(path.join(os.tmpdir(), prefix));

test("validates citations and verbatim quotes", () => {
  assert.ok(validateOutcome(reply, "Fix the bug", followup, ["Fix the bug"]));
  assert.ok(!validateOutcome({ ...reply, evidence: [{ ref: "session:other", quote: "Still stuck" }] }, "Fix the bug", followup));
  assert.ok(!validateOutcome({ ...reply, evidence: [{ ref: "trace", quote: "invented" }] }, "Fix the bug", followup));
  assert.ok(!validateOutcome({ ...reply, evidence: [{ ref: "session:later", quote: "invented" }] }, "Fix the bug", followup));
  assert.ok(!validateOutcome({ ...reply, evidence: [{ ref: "session:later", quote: "session:later" }] }, "Fix the bug", followup));
  assert.ok(!validateOutcome(reply, "Fix the bug", followup, []));
  // A question the reply settled claims nothing about later, so it cites nothing.
  assert.ok(validateOutcome({ ...reply, label: "answered", evidence: [] }, "Fix the bug", followup));
  assert.ok(!validateOutcome({ ...reply, label: "advanced", evidence: [] }, "Fix the bug", followup));
  assert.ok(!validateOutcome({ ...reply, label: "done" }, "Fix the bug", followup, ["Fix the bug"]));
});

test("CLI leaves an unscorable session alone without failing or printing private evidence", async () => {
  const dir = tmp("outcome-cli-");
  writeJson(evidenceFile(dir, "x", "claude"), { harness: "claude", transcriptId: "x", status: "ok", endedAt: "2020-01-01T00:00:00Z", outcomeSnapshot: { trace: "PRIVATE QUOTE" } });
  const server = await fakeLangfuse().serve();
  try {
    const { stdout, stderr } = await execFileAsync(process.execPath, ["bin/ca-improve.js", "outcome", "--state-dir", dir, "--analyzer", "mock"], { cwd: path.resolve("."), env: { ...process.env, ...server.env } });
    assert.equal(JSON.parse(stdout).unscored, 1);
    assert.doesNotMatch(stdout + stderr, /PRIVATE QUOTE/);
  } finally {
    await server.close();
  }
  assert.deepEqual(fs.readdirSync(dir), ["evidence"]);
});

test("maturation, preview, unscored sessions, and explicit rescore", async () => {
  const dir = tmp("outcome-test-");
  const end = Date.parse("2026-01-01T00:00:00Z");
  const lf = fakeLangfuse();
  lf.add("claude", "x", { start: end - 60_000, turns: [{ user: "Fix the bug", assistant: "Looking" }] });
  const read = await readTranscript({ harness: "claude", id: "x" }, { client: lf.client });
  const record = { harness: "claude", transcriptId: "x", status: "ok", source: null, startedAt: 5, endedAt: new Date(end).toISOString(), positive: [1], negative: [], gaps: [], outcomeSnapshot: { revision: read.revision, trace: "Fix the bug", texts: ["Fix the bug"], firstUserMessage: "Fix the bug" } };
  const file = evidenceFile(dir, "x", "claude");
  writeJson(file, record);
  const options = { client: lf.client, stateDir: dir, now: end + 3 * DAY, collect: async () => followup, invoke: async (_role, prompt) => { assert.ok(!prompt.includes("SOUL_BASELINE")); return reply; } };
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
  assert.equal(readJson(file).outcome.rubric.matureDays, 3);
  assert.deepEqual(readJson(file).positive, [1]);
  assert.equal((await runOutcome(options)).selected, 0);
  assert.equal((await runOutcome({ ...options, rescore: true })).scored, 1);
  lf.add("claude", "x", { start: end + DAY, turns: [{ user: "reopened", assistant: "ok" }] });
  assert.equal((await runOutcome({ ...options, rescore: true })).unscored, 1);
  assert.deepEqual(fs.readdirSync(dir).sort(), ["evidence", "outcome-preview"]);
});

test("a dry run previews finished Hermes sessions that were never analyzed", async () => {
  const dir = path.join(tmp("outcome-backtest-"), "state"), end = Date.parse("2026-01-01T00:00:00Z"), now = end + 10 * DAY;
  const lf = fakeLangfuse();
  const turns = [{ user: "Fix the bug", assistant: "On it" }];
  lf.add("hermes", "desk", { start: end - 60_000, platform: "desktop", turns });
  lf.add("hermes", "cron", { start: end - 60_000, platform: "cron", turns });
  lf.add("hermes", "fresh", { start: now - 30 * 60_000, platform: "desktop", turns });
  lf.add("claude", "other-harness", { start: end - 60_000, turns });
  const seen = [];
  const options = { client: lf.client, stateDir: dir, now, invoke: async () => reply, collect: async ({ session, candidates }) => { seen.push([session.transcriptId, session.endedAt, (await candidates()).length]); return followup; } };
  assert.equal((await runOutcome(options)).selected, 0);
  const preview = await runOutcome({ ...options, dryRun: true });
  assert.deepEqual([preview.selected, preview.scored, preview.unscored], [2, 2, 0]);
  assert.deepEqual(seen.map(([id, ended]) => [id, ended]).sort(), [["cron", new Date(end).toISOString()], ["desk", new Date(end).toISOString()]]);
  assert.ok(seen.every(([, , count]) => count === 3), "the open session is not a candidate yet");
  const rows = fs.readFileSync(preview.preview, "utf8").trim().split("\n").map((line) => JSON.parse(line));
  assert.deepEqual(rows.map((row) => row.source).sort(), ["cron", "desktop"]);
  assert.ok(!fs.existsSync(path.join(dir, "evidence")));
});

test("a snapshot cut from a local store is re-cut once from Langfuse; a later turn makes it unscorable", async () => {
  const dir = tmp("outcome-legacy-");
  const end = Date.parse("2026-01-01T00:00:00Z");
  const lf = fakeLangfuse();
  lf.add("hermes", "x", { start: end - 60_000, turns: [{ user: "Fix the bug", assistant: "Fixed" }] });
  const file = evidenceFile(dir, "x", "hermes");
  const legacy = { location: { harness: "hermes", id: "x", db: "/home/u/.hermes/state.db" }, revision: { version: 2, harness: "hermes", id: "x", sha256: "abc" }, trace: "Fix the bug", texts: ["Fix the bug"] };
  writeJson(file, { harness: "hermes", transcriptId: "x", status: "ok", endedAt: new Date(end).toISOString(), outcomeSnapshot: legacy });
  const options = { client: lf.client, stateDir: dir, now: end + 4 * DAY, collect: async () => followup, invoke: async () => reply, rescore: true };
  assert.equal((await runOutcome({ ...options, dryRun: true })).scored, 1);
  assert.deepEqual(readJson(file).outcomeSnapshot, legacy, "a dry run never rewrites evidence");
  assert.equal((await runOutcome(options)).scored, 1);
  const saved = readJson(file).outcomeSnapshot;
  assert.equal(saved.revision.source, "langfuse");
  assert.deepEqual(saved.location, { harness: "hermes", id: "x" });
  assert.match(saved.trace, /Fix the bug/);
  lf.add("hermes", "x", { start: end + DAY, turns: [{ user: "reopened", assistant: "ok" }] });
  assert.deepEqual([(await runOutcome(options)).scored, (await runOutcome(options)).unscored], [0, 1]);
  assert.deepEqual(readJson(file).outcomeSnapshot, saved, "a changed session is not re-cut");
});

test("snapshots keep only the session reference", () => {
  const snapshot = outcomeSnapshot({ harness: "claude", id: "x", cwd: "/p" }, [{ kind: "message", role: "user", text: "hi" }], { source: "langfuse" });
  assert.deepEqual(snapshot.location, { harness: "claude", id: "x" });
});
