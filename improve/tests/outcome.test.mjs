import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { runOutcome, validateOutcome } from "../src/outcome.js";
import { evidenceFile, writeJson } from "../src/state.js";

const followup = { sessions: [{ ref: "session:later", firstUser: "Still stuck" }], commits: [], journal: [] };
const reply = { aim: "Fix the bug", label: "stalled", reason: "It remains", evidence: [{ ref: "trace", quote: "Fix the bug" }] };
test("validates citations and verbatim quotes", () => {
  assert.ok(validateOutcome(reply, "Fix the bug", followup));
  assert.ok(!validateOutcome({ ...reply, evidence: [{ ref: "session:other", quote: "Still stuck" }] }, "Fix the bug", followup));
  assert.ok(!validateOutcome({ ...reply, evidence: [{ ref: "trace", quote: "invented" }] }, "Fix the bug", followup));
  assert.ok(!validateOutcome({ ...reply, evidence: [{ ref: "session:later", quote: "invented" }] }, "Fix the bug", followup));
});
test("maturation, preview, failures, and explicit rescore", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "outcome-test-"));
  const transcript = path.join(dir, "trace.jsonl");
  fs.writeFileSync(transcript, JSON.stringify({ type: "user", message: { role: "user", content: "Fix the bug" } }) + "\n");
  const record = { harness: "claude", transcriptId: "x", status: "ok", endedAt: "2026-01-01T00:00:00Z", positive: [1], negative: [], gaps: [] };
  const file = evidenceFile(dir, "x", "claude");
  writeJson(file, record);
  const options = { stateDir: dir, now: Date.parse("2026-01-04T00:00:00Z"), transcripts: [{ harness: "claude", id: "x", path: transcript }], collect: async () => followup, invoke: async (_role, prompt) => { assert.ok(!prompt.includes("SOUL_BASELINE")); return reply; } };
  const before = fs.readFileSync(file, "utf8");
  const preview = await runOutcome({ ...options, dryRun: true });
  assert.equal(preview.scored, 1);
  assert.equal(fs.readFileSync(file, "utf8"), before);
  assert.equal(JSON.parse(fs.readFileSync(preview.preview, "utf8")).outcome.label, "stalled");
  assert.equal((await runOutcome({ ...options, now: options.now - 1 })).selected, 0);
  assert.equal((await runOutcome({ ...options, invoke: async () => ({ ...reply, evidence: [] }) })).failed, 1);
  assert.equal(fs.readFileSync(file, "utf8"), before);
  assert.equal((await runOutcome(options)).scored, 1);
  assert.deepEqual(JSON.parse(fs.readFileSync(file)).positive, [1]);
  assert.equal((await runOutcome(options)).selected, 0);
  assert.equal((await runOutcome({ ...options, rescore: true })).scored, 1);
});
