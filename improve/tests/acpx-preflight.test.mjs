import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

import {
  resolveAcpxBin,
  checkAcpxAvailable,
  assertAcpxAvailable,
} from "../src/analyze.js";
import { runPipeline } from "../src/pipeline.js";

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "ca-acpx-preflight-"));
}

function homeWithTranscripts(n = 1) {
  const home = tmpDir();
  const dir = path.join(home, ".codex", "sessions");
  fs.mkdirSync(dir, { recursive: true });
  for (let i = 0; i < n; i += 1) {
    const payload = JSON.stringify({ role: "user", text: `bootstrap context please ${i}` });
    fs.writeFileSync(path.join(dir, `2026-01-0${i + 1}T00-00-00Z.jsonl`), `${payload}\n`, "utf8");
  }
  return home;
}

async function withEnv(vars, fn) {
  const saved = new Map();
  for (const [key, value] of Object.entries(vars)) {
    saved.set(key, process.env[key]);
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  try {
    return await fn();
  } finally {
    for (const [key, value] of saved) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
}

function dirIsEmpty(dir) {
  try {
    return fs.readdirSync(dir).length === 0;
  } catch {
    return true;
  }
}

describe("acpx availability preflight (real production run path)", () => {
  it("respects CA_IMPROVE_ACPX_BIN / BACKPASS_ACPX_BIN selection order", async () => {
    await withEnv({ CA_IMPROVE_ACPX_BIN: "/bin/ca-acpx", BACKPASS_ACPX_BIN: "/bin/bp-acpx" }, async () => {
      assert.equal(resolveAcpxBin(), "/bin/ca-acpx");
    });
    await withEnv({ CA_IMPROVE_ACPX_BIN: undefined, BACKPASS_ACPX_BIN: "/bin/bp-acpx" }, async () => {
      assert.equal(resolveAcpxBin(), "/bin/bp-acpx");
    });
    await withEnv({ CA_IMPROVE_ACPX_BIN: undefined, BACKPASS_ACPX_BIN: undefined }, async () => {
      assert.equal(resolveAcpxBin(), "acpx");
    });
  });

  it("reports a missing binary with remediation and no side effects", () => {
    const missing = "/nonexistent-ca-acpx-binary-xyz";
    const result = checkAcpxAvailable({ bin: missing });
    assert.equal(result.ok, false);
    assert.equal(result.bin, missing);
    assert.ok(/acpx binary not available/.test(result.error));
    assert.ok(/CA_IMPROVE_ACPX_BIN/.test(result.error));
    assert.ok(/No traces were analyzed/.test(result.error));
    assert.throws(() => assertAcpxAvailable({ bin: missing }), /acpx binary not available/);
  });

  it("fails fast on the real production path before trace analysis with no trace evidence", async () => {
    const home = homeWithTranscripts(2);
    const stateDir = tmpDir();
    const missing = "/nonexistent-ca-acpx-binary-xyz";
    await withEnv({ CA_IMPROVE_ACPX_BIN: missing, BACKPASS_ACPX_BIN: undefined }, async () => {
      await assert.rejects(
        runPipeline({ home, stateDir, analyzer: "acpx", runId: "run-PREFLIGHT" }),
        /acpx binary not available/,
      );
    });
    // No per-trace prompts, evidence, ledger, or proposal were written.
    assert.ok(dirIsEmpty(path.join(stateDir, "prompts")), "no prompts archived");
    assert.ok(dirIsEmpty(path.join(stateDir, "evidence")), "no evidence written");
    assert.ok(!fs.existsSync(path.join(stateDir, "ledger.json")), "no ledger written");
    assert.ok(!fs.existsSync(path.join(stateDir, "proposal.json")), "no proposal written");
  });

  it("honours BACKPASS_ACPX_BIN fallback selection on the real path", async () => {
    const home = homeWithTranscripts(1);
    const stateDir = tmpDir();
    await withEnv(
      { CA_IMPROVE_ACPX_BIN: undefined, BACKPASS_ACPX_BIN: "/nonexistent-backpass-acpx-xyz" },
      async () => {
        await assert.rejects(
          runPipeline({ home, stateDir, analyzer: "acpx", runId: "run-PREFLIGHT-BP" }),
          /nonexistent-backpass-acpx-xyz/,
        );
      },
    );
    assert.ok(dirIsEmpty(path.join(stateDir, "prompts")));
  });

  it("mock runs and injected invokes bypass the preflight (no real acpx)", async () => {
    const home = homeWithTranscripts(1);
    await withEnv({ CA_IMPROVE_ACPX_BIN: "/nonexistent-ca-acpx-binary-xyz" }, async () => {
      const mockProposal = await runPipeline({
        home,
        stateDir: tmpDir(),
        analyzer: "mock",
        runId: "run-PREFLIGHT-MOCK",
      });
      assert.ok(Array.isArray(mockProposal.edits));
      const injected = await runPipeline({
        home,
        stateDir: tmpDir(),
        analyzer: "acpx",
        runId: "run-PREFLIGHT-INJECTED",
        analyzeInvoke: () => ({ status: "failed", error: "injected" }),
        consolidateInvoke: () => ({ status: "failed", error: "injected" }),
        synthesizeInvoke: () => ({ status: "failed", error: "injected" }),
        annotateInvoke: () => ({ status: "failed", error: "injected" }),
      });
      assert.ok(Array.isArray(injected.edits));
    });
  });
});
