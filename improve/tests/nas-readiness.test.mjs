import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { writeProposal, readJson } from "../src/state.js";
import { discoverTranscripts } from "../src/discovery.js";
import { defaultRepoRoot } from "../src/analyze.js";
import { defaultSoulPath } from "../src/soul.js";

function tmp() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "ca-nas-"));
}

test("writeProposal archives an unapplied predecessor before replacing it", () => {
  const stateDir = tmp();
  writeProposal(stateDir, { id: "prop-a", appliedAt: null, edits: [] });
  writeProposal(stateDir, { id: "prop-b", appliedAt: null, edits: [] });
  assert.equal(readJson(path.join(stateDir, "proposal.json")).id, "prop-b");
  assert.equal(readJson(path.join(stateDir, "proposals", "prop-a.json")).id, "prop-a");
});

test("writeProposal does not archive an applied predecessor", () => {
  const stateDir = tmp();
  writeProposal(stateDir, { id: "prop-a", appliedAt: "2026-11-13T00:00:00+00:00", edits: [] });
  writeProposal(stateDir, { id: "prop-b", appliedAt: null, edits: [] });
  assert.equal(fs.existsSync(path.join(stateDir, "proposals")), false);
});

test("strict discovery fails on a missing named store; default stays fail-soft", () => {
  const home = tmp();
  const stateDir = path.join(tmp(), "state");
  assert.throws(
    () => discoverTranscripts({ home, stateDir, harnesses: ["hermes"], strict: true }),
    /hermes: store missing/,
  );
  const soft = discoverTranscripts({ home, stateDir, harnesses: ["hermes"] });
  assert.equal(soft.perHarness.hermes.error, "store missing");
});

test("CA_WORKSPACE_ROOT redirects the live SOUL and experience root", () => {
  const live = tmp();
  const previous = process.env.CA_WORKSPACE_ROOT;
  process.env.CA_WORKSPACE_ROOT = live;
  try {
    assert.equal(defaultRepoRoot(), path.resolve(live));
    assert.equal(defaultSoulPath(), path.join(path.resolve(live), "workspaces", "alignment", "artifacts", "SOUL.md"));
  } finally {
    if (previous === undefined) delete process.env.CA_WORKSPACE_ROOT;
    else process.env.CA_WORKSPACE_ROOT = previous;
  }
});
