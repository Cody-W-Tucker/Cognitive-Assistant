import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { writeProposal, readJson, defaultStateDir, defaultExperienceRoot } from "../src/state.js";
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

test("CA_HOME holds state and lineage; the living SOUL wins over bootstrap once compiled", () => {
  const home = tmp();
  const previous = process.env.CA_HOME;
  process.env.CA_HOME = home;
  try {
    assert.equal(defaultStateDir(), path.join(home, "improve"));
    assert.equal(defaultExperienceRoot(), path.join(home, "experience"));
    const bootstrap = path.join(defaultRepoRoot(), "workspaces", "alignment", "artifacts", "SOUL.md");
    assert.equal(defaultSoulPath(), bootstrap);
    fs.mkdirSync(path.join(home, "soul"), { recursive: true });
    fs.writeFileSync(path.join(home, "soul", "current.md"), "living\n");
    assert.equal(defaultSoulPath(), path.join(home, "soul", "current.md"));
  } finally {
    if (previous === undefined) delete process.env.CA_HOME;
    else process.env.CA_HOME = previous;
  }
});
