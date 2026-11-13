import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import { assertMinGapEvidence, evidenceFile, persistPrompt, readJson, readRejections, writeProposal } from "../src/state.js";
import { tmpDir } from "./helpers.mjs";

test("writeProposal archives an unapplied predecessor before replacing it", () => {
  const stateDir = tmpDir();
  writeProposal(stateDir, { id: "prop-a", appliedAt: null, edits: [] });
  writeProposal(stateDir, { id: "prop-b", appliedAt: null, edits: [] });
  assert.equal(readJson(path.join(stateDir, "proposal.json")).id, "prop-b");
  assert.equal(readJson(path.join(stateDir, "proposals", "prop-a.json")).id, "prop-a");
});

test("writeProposal does not archive an applied predecessor", () => {
  const stateDir = tmpDir();
  writeProposal(stateDir, { id: "prop-a", appliedAt: "2026-11-13T00:00:00+00:00", edits: [] });
  writeProposal(stateDir, { id: "prop-b", appliedAt: null, edits: [] });
  assert.equal(fs.existsSync(path.join(stateDir, "proposals")), false);
});

test("persisted prompts are private and hostile ids cannot escape the prompts dir", () => {
  const stateDir = tmpDir();
  const file = persistPrompt(stateDir, { runId: "run-1", name: "../../etc/passwd", prompt: "p" });
  assert.equal(path.dirname(file), path.join(stateDir, "prompts"));
  assert.equal(fs.statSync(file).mode & 0o777, 0o600);
  assert.equal(readJson(file.replace(/\.md$/, ".json")).name, "../../etc/passwd");
});

test("malformed rejection lines are skipped", () => {
  const stateDir = tmpDir();
  fs.writeFileSync(path.join(stateDir, "rejections.jsonl"), '{"clusterId":"g-a"}\nnot json\n\n{"title":"t"}\n');
  assert.deepEqual(readRejections(stateDir), [{ clusterId: "g-a" }, { title: "t" }]);
  assert.deepEqual(readRejections(tmpDir()), []);
});

test("the evidence floor must be an integer of at least 2", () => {
  for (const ok of [2, 3, "4"]) assert.equal(assertMinGapEvidence(ok), Number(ok));
  for (const bad of [1, 0, -2, 2.5, "x", null]) assert.throws(() => assertMinGapEvidence(bad), /integer >= 2/);
});

test("a session id cannot place its evidence outside evidence/", () => {
  const stateDir = tmpDir();
  const evidenceDir = path.join(stateDir, "evidence");
  for (const id of ["../../escape", "a/b", "..\\x", "plain-id"]) {
    assert.equal(path.dirname(evidenceFile(stateDir, id)), evidenceDir, id);
  }
  assert.equal(path.basename(evidenceFile(stateDir, "plain-id")), "plain-id.json");
});
