import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { materializeValidatedPlans } from "../src/synthesize.js";

function validLedger() {
  return { clusters: [{ id: "c1", eligible: true, sources: ["s1", "s2"] }] };
}

function validPlan(id = "e1") {
  return {
    id,
    kind: "add",
    clusterId: "c1",
    provisionalIntent: "Fix gap",
    provisionalSources: ["s1", "s2"],
    provisionalCount: 2,
  };
}

describe("materializeValidatedPlans descriptor-relative race rejection", () => {
  it("swapping a pinned intermediate for a symlink before final open is rejected with no outside write", () => {
    const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-fdrace-state-"));
    const outsideDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-fdrace-out-"));
    const outsideFile = path.join(outsideDir, "secret.md");
    fs.writeFileSync(outsideFile, "outside-original\n", "utf8");
    const base = path.join(stateDir, "synthesis-workspace");
    const runDir = path.join(base, "runA");
    fs.mkdirSync(runDir, { recursive: true });
    // Deterministic TOCTOU seam: after the workspace directories are pinned
    // by held descriptors but before the final file open, replace the
    // checked intermediate with a symlink to the outside dir.
    const raceHook = () => {
      fs.rmSync(runDir, { recursive: true, force: true });
      fs.symlinkSync(outsideDir, runDir);
    };
    const prevNodeEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = "test";
    try {
      assert.throws(
        () =>
          materializeValidatedPlans([validPlan("e1")], {
            stateDir,
            workspaceRoot: runDir,
            ledger: validLedger(),
            _beforeFinalOpen: raceHook,
          }),
        /symlink/,
      );
    } finally {
      if (prevNodeEnv === undefined) delete process.env.NODE_ENV;
      else process.env.NODE_ENV = prevNodeEnv;
    }
    assert.equal(fs.readFileSync(outsideFile, "utf8"), "outside-original\n");
    assert.equal(fs.existsSync(path.join(outsideDir, "e1.md")), false);
    assert.equal(fs.lstatSync(runDir).isSymbolicLink(), true);
    fs.rmSync(stateDir, { recursive: true, force: true });
    fs.rmSync(outsideDir, { recursive: true, force: true });
  });

  it("no hook still materializes into a nested workspace root", () => {
    const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-fdrace-ok-"));
    try {
      const nested = path.join(stateDir, "synthesis-workspace", "runB", "sub");
      const out = materializeValidatedPlans([validPlan("e1")], {
        stateDir,
        workspaceRoot: nested,
        ledger: validLedger(),
      });
      assert.deepEqual(out.written, ["e1.md"]);
      assert.ok(fs.existsSync(path.join(nested, "e1.md")));
    } finally {
      fs.rmSync(stateDir, { recursive: true, force: true });
    }
  });
});
