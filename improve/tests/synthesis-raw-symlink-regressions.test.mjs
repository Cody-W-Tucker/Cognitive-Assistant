import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { EventEmitter } from "node:events";

import { runAcpxPromptFile, runAcpxPromptFileAsync } from "../src/acpx-text.js";
import {
  acpxSynthesisInvoke,
  materializeValidatedPlans,
  parseStrictBoundedSynthesisStdout,
} from "../src/synthesize.js";

function makeTempPrompt() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-synth-raw-"));
  const file = path.join(dir, "prompt.md");
  fs.writeFileSync(file, "# prompt\n", "utf8");
  return { dir, file };
}

const syncSpawn = (stdout) => () => ({ status: 0, stdout, stderr: "" });

function makeAsyncSpawn(stdoutText, exitCode = 0) {
  return () => {
    const child = new EventEmitter();
    child.stdout = new EventEmitter();
    child.stderr = new EventEmitter();
    child.kill = () => {};
    queueMicrotask(() => {
      child.stdout.emit("data", Buffer.from(String(stdoutText)));
      child.emit("close", exitCode);
    });
    return child;
  };
}

describe("synthesis raw-stdout boundary (sync)", () => {
  it("prose synthesis stdout fails strict path", () => {
    const { file } = makeTempPrompt();
    const out = acpxSynthesisInvoke({
      promptFile: file,
      model: "test-model",
      spawnFn: syncSpawn('prose before {"plans":[]} prose after'),
    });
    assert.equal(out.status, "failed");
  });

  it("fenced synthesis stdout fails strict path", () => {
    const { file } = makeTempPrompt();
    const out = acpxSynthesisInvoke({
      promptFile: file,
      model: "test-model",
      spawnFn: syncSpawn('```json\n{"plans":[]}\n```'),
    });
    assert.equal(out.status, "failed");
  });

  it("exact {\"plans\":[]} succeeds", () => {
    const { file } = makeTempPrompt();
    const out = acpxSynthesisInvoke({
      promptFile: file,
      model: "test-model",
      spawnFn: syncSpawn('{"plans":[]}'),
    });
    assert.equal(out.status, "ok");
    assert.deepEqual(out.plans, []);
  });

  it("sync runAcpxPromptFile rejects prose synthesis stdout", () => {
    const { file } = makeTempPrompt();
    const raw = 'prose {"plans":[]} tail';
    const out = runAcpxPromptFile({
      role: "synthesis",
      promptFile: file,
      model: "test-model",
      spawnFn: syncSpawn(raw),
    });
    assert.equal(out.status, "failed");
    assert.equal(parseStrictBoundedSynthesisStdout(raw), null);
  });
});

describe("synthesis raw-stdout boundary (async)", () => {
  it("prose synthesis stdout fails at helper", async () => {
    const { file } = makeTempPrompt();
    const raw = 'prose before {"plans":[]} prose after';
    const out = await runAcpxPromptFileAsync({
      role: "synthesis",
      promptFile: file,
      model: "test-model",
      spawnFn: makeAsyncSpawn(raw),
    });
    assert.equal(out.status, "failed");
    assert.equal(parseStrictBoundedSynthesisStdout(raw), null);
  });

  it("fenced synthesis stdout fails at helper", async () => {
    const { file } = makeTempPrompt();
    const raw = '```json\n{"plans":[]}\n```';
    const out = await runAcpxPromptFileAsync({
      role: "synthesis",
      promptFile: file,
      model: "test-model",
      spawnFn: makeAsyncSpawn(raw),
    });
    assert.equal(out.status, "failed");
    assert.equal(parseStrictBoundedSynthesisStdout(raw), null);
  });

  it("exact {\"plans\":[]} passes at helper", async () => {
    const { file } = makeTempPrompt();
    const raw = '{"plans":[]}';
    const out = await runAcpxPromptFileAsync({
      role: "synthesis",
      promptFile: file,
      model: "test-model",
      spawnFn: makeAsyncSpawn(raw),
    });
    assert.equal(out.status, "ok");
    assert.deepEqual(out.result, { plans: [] });
    assert.deepEqual(parseStrictBoundedSynthesisStdout(String(out.stdout)), { plans: [] });
  });
});

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

describe("materializeValidatedPlans symlink fail-closed", () => {
  it("pre-created e1.md symlink target does not write outside", () => {
    const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-mat-state-"));
    const outsideDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-mat-out-"));
    const outsideFile = path.join(outsideDir, "secret.md");
    fs.writeFileSync(outsideFile, "outside-original\n", "utf8");
    const base = path.join(stateDir, "synthesis-workspace");
    fs.mkdirSync(base, { recursive: true });
    const linkTarget = path.join(base, "e1.md");
    fs.symlinkSync(outsideFile, linkTarget);
    assert.throws(
      () => materializeValidatedPlans([validPlan("e1")], { stateDir, ledger: validLedger() }),
      /symlink/,
    );
    assert.equal(fs.readFileSync(outsideFile, "utf8"), "outside-original\n");
    assert.equal(fs.lstatSync(linkTarget).isSymbolicLink(), true);
  });

  it("symlinked workspace root fails closed", () => {
    const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-mat-root-"));
    const outsideDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-mat-root-out-"));
    const base = path.join(stateDir, "synthesis-workspace");
    fs.mkdirSync(stateDir, { recursive: true });
    fs.symlinkSync(outsideDir, base);
    assert.throws(
      () => materializeValidatedPlans([validPlan("e1")], { stateDir, ledger: validLedger() }),
      /symlink/,
    );
  });

  it("symlinked intermediate workspace component fails closed", () => {
    const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-mat-mid-"));
    const outsideDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-mat-mid-out-"));
    const base = path.join(stateDir, "synthesis-workspace");
    const runDir = path.join(base, "runA");
    fs.mkdirSync(base, { recursive: true });
    fs.symlinkSync(outsideDir, runDir);
    const nested = path.join(runDir, "sub");
    assert.throws(
      () =>
        materializeValidatedPlans([validPlan("e1")], {
          stateDir,
          workspaceRoot: nested,
          ledger: validLedger(),
        }),
      /symlink/,
    );
    assert.equal(fs.existsSync(path.join(outsideDir, "sub")), false);
  });

  it("stateDir under a symlinked parent ancestry fails closed (no write via link)", () => {
    const sandbox = fs.mkdtempSync(path.join(os.tmpdir(), "ca-mat-anc-"));
    const realParent = path.join(sandbox, "real-parent");
    fs.mkdirSync(realParent, { recursive: true });
    const linkParent = path.join(sandbox, "link-parent");
    fs.symlinkSync(realParent, linkParent);
    const linkedState = path.join(linkParent, "state");
    try {
      assert.throws(
        () => materializeValidatedPlans([validPlan("e1")], { stateDir: linkedState, ledger: validLedger() }),
        /symlink/,
      );
      assert.equal(fs.existsSync(path.join(realParent, "state", "synthesis-workspace", "e1.md")), false);
      assert.equal(fs.existsSync(path.join(realParent, "state", "e1.md")), false);
    } finally {
      fs.rmSync(sandbox, { recursive: true, force: true });
    }
  });

  it("normal absolute stateDir still materializes", () => {
    const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-mat-ok-"));
    try {
      const out = materializeValidatedPlans([validPlan("e1")], { stateDir, ledger: validLedger() });
      assert.deepEqual(out.written, ["e1.md"]);
      assert.ok(fs.existsSync(path.join(stateDir, "synthesis-workspace", "e1.md")));
    } finally {
      fs.rmSync(stateDir, { recursive: true, force: true });
    }
  });
});
