// Option 2 focused tests: production ACPX text-only interpreter/proposer,
// strict bounded stdout payload, deterministic materialization, central
// minGapEvidence floor. Mocks preserved; no synthetic provenance/fallback.
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  synthesizeWithAcpx,
  validateProvisionalPlans,
  materializeValidatedPlans,
  buildSynthesisPrompt,
  acpxSynthesisInvoke,
  SYNTHESIS_MAX_PLANS,
  SYNTHESIS_STDOUT_MAX_CHARS,
} from "../src/synthesize.js";
import { assertMinGapEvidence } from "../src/state.js";

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "ca-txtonly-"));
}

function ledger() {
  return {
    version: 1,
    minGapEvidence: 2,
    clusters: [
      {
        id: "g-aaa",
        proposedInstruction: "Bootstrap context once",
        representativeQuote: "sessions re-derive project context from scratch",
        mistake: "sessions re-derive project context from scratch",
        sources: ["s1", "s2"],
        count: 2,
        eligible: true,
        perSource: {
          s1: { quote: "sessions re-derive project context from scratch", mistake: "m" },
          s2: { quote: "sessions re-derive project context from scratch", mistake: "m" },
        },
      },
      {
        id: "g-inelig",
        proposedInstruction: "Ineligible",
        representativeQuote: "zzz",
        mistake: "zzz",
        sources: ["sx"],
        count: 1,
        eligible: false,
        perSource: { sx: { quote: "zzz", mistake: "m" } },
      },
    ],
  };
}

function idx() {
  return new Map([
    ["s1", [{ quote: "sessions re-derive project context from scratch" }]],
    ["s2", [{ quote: "sessions re-derive project context from scratch" }]],
  ]);
}

function validPlan(overrides = {}) {
  return {
    id: "e1",
    kind: "add",
    clusterId: "g-aaa",
    provisionalIntent: "Bootstrap context once",
    provisionalSources: ["s1", "s2"],
    ...overrides,
  };
}

describe("text-only invocation (no workspace/cwd, bounded stdout)", () => {
  it("production invoke receives no workspace/cwd and prompt never asks to inspect/edit workspace/edit turn", () => {
    const stateDir = tmpDir();
    let seen = null;
    const out = synthesizeWithAcpx(ledger(), {
      evidenceIndex: idx(),
      invoke: (args) => {
        seen = args;
        return { status: "ok", plans: [validPlan()] };
      },
      stateDir,
      runId: "run-TXT",
      soulSnapshot: "soul snapshot",
      soulSha256: "abc123",
    });
    assert.equal(out.edits.length, 1);
    assert.equal(seen.workspace, undefined);
    assert.equal(seen.cwd, undefined);
    assert.equal(seen.workspaceRoot, undefined);
    const prompt = buildSynthesisPrompt(ledger(), {
      evidenceIndex: idx(),
      soulSnapshot: "soul snapshot",
      soulSha256: "abc123",
    });
    assert.ok(/text-only/i.test(prompt));
    assert.ok(!/edit turn/i.test(prompt));
    assert.ok(!/inspect and edit ONLY/i.test(prompt));
    assert.ok(!/invocation cwd/i.test(prompt));
  });

  it("acpxSynthesisInvoke rejects workspace/cwd options fail-closed", () => {
    assert.throws(() => acpxSynthesisInvoke({ prompt: "x", promptFile: "f", workspace: "/tmp/w" }), /text-only/);
    assert.throws(() => acpxSynthesisInvoke({ prompt: "x", promptFile: "f", cwd: "/tmp/w" }), /text-only/);
    assert.throws(() => acpxSynthesisInvoke({ prompt: "x", promptFile: "f", workspaceRoot: "/tmp/w" }), /text-only/);
  });

  it("bounded payload: oversize plans array and oversize stdout fail closed", () => {
    const many = Array.from({ length: SYNTHESIS_MAX_PLANS + 1 }, (_, i) => validPlan({ id: `e${i}` }));
    const check = validateProvisionalPlans({ plans: many }, { ledger: ledger(), floor: 2 });
    assert.equal(check.ok, false);
    assert.ok(/exceeds/.test(check.errors.join(";")));
    const big = "x".repeat(SYNTHESIS_STDOUT_MAX_CHARS + 1);
    assert.ok(big.length > SYNTHESIS_STDOUT_MAX_CHARS);
  });
});

describe("strict stdout schema/provenance validation (fail-closed)", () => {
  it("rejects malformed, candidates/edits keys, and non-array plans", () => {
    for (const raw of [null, [], {}, { plans: "nope" }, { candidates: [] }, { edits: [] }, { plans: [{ clusterId: "" }] }]) {
      const out = synthesizeWithAcpx(ledger(), {
        evidenceIndex: idx(),
        invoke: () => ({ status: "ok", result: raw }),
        stateDir: tmpDir(),
        soulSnapshot: "soul snapshot",
        soulSha256: "abc123",
      });
      assert.deepEqual(out.edits, [], JSON.stringify(raw));
      assert.ok(out.failed, JSON.stringify(raw));
    }
  });

  it("rejects unknown/ineligible clusters and <2 distinct known sources", () => {
    const cases = [
      validPlan({ clusterId: "g-ghost" }),
      validPlan({ clusterId: "g-inelig", provisionalSources: ["sx", "s1"] }),
      validPlan({ provisionalSources: ["s1"] }),
      validPlan({ provisionalSources: ["s1", "s1"] }),
      validPlan({ provisionalSources: ["s1", "ghost"] }),
    ];
    for (const plan of cases) {
      const check = validateProvisionalPlans({ plans: [plan] }, { ledger: ledger(), floor: 2 });
      assert.equal(check.ok, false, JSON.stringify(plan));
    }
  });

  it("rejects authoritative final fields, path-like and unexpected fields, duplicate/unsafe ids", () => {
    const badFields = [
      { ...validPlan(), record: { title: "x" } },
      { ...validPlan(), title: "x" },
      { ...validPlan(), body: "x" },
      { ...validPlan(), evidence: [] },
      { ...validPlan(), file: "e1.md" },
      { ...validPlan(), path: "/tmp/x" },
      { ...validPlan(), workspace: "/tmp/w" },
      { ...validPlan(), cwd: "/tmp/w" },
      { ...validPlan(), unexpectedKey: 1 },
      { ...validPlan(), id: "../evil" },
      { ...validPlan(), id: "/abs/path" },
      { ...validPlan(), clusterId: "../evil" },
      { ...validPlan(), provisionalSources: ["s1", "/tmp/evil"] },
    ];
    for (const plan of badFields) {
      const check = validateProvisionalPlans({ plans: [plan] }, { ledger: ledger(), floor: 2 });
      assert.equal(check.ok, false, JSON.stringify(plan));
    }
    const dupes = validateProvisionalPlans({ plans: [validPlan({ id: "e1" }), validPlan({ id: "e1" })] }, { ledger: ledger(), floor: 2 });
    assert.equal(dupes.ok, false);
  });
});

describe("deterministic materialization (code-only, no model-controlled path)", () => {
  it("writes only validated markdown under existing stateDir/synthesis-workspace", () => {
    const stateDir = tmpDir();
    const out = synthesizeWithAcpx(ledger(), {
      evidenceIndex: idx(),
      invoke: () => ({ status: "ok", plans: [validPlan({ id: "e7" })] }),
      stateDir,
      runId: "run-MAT1",
      soulSnapshot: "soul snapshot",
      soulSha256: "abc123",
    });
    assert.equal(out.edits.length, 1);
    const file = path.join(stateDir, "synthesis-workspace", "e7.md");
    assert.ok(fs.existsSync(file));
    const body = fs.readFileSync(file, "utf8");
    assert.ok(body.includes("clusterId: g-aaa"));
    assert.ok(body.includes("s1") && body.includes("s2"));
    // No model-controlled path target: plans carrying file/path are rejected, never written.
    const evil = synthesizeWithAcpx(ledger(), {
      evidenceIndex: idx(),
      invoke: () => ({ status: "ok", plans: [{ ...validPlan(), file: "../../evil.md" }] }),
      stateDir: tmpDir(),
      soulSnapshot: "soul snapshot",
      soulSha256: "abc123",
    });
    assert.deepEqual(evil.edits, []);
  });

  it("materialize refuses duplicate/unsafe ids and escapes fail-closed", () => {
    const stateDir = tmpDir();
    assert.throws(() => materializeValidatedPlans([{ id: "../evil", clusterId: "g-aaa", provisionalIntent: "x", provisionalSources: ["s1", "s2"] }], { stateDir }), /refuse|unsafe/);
    assert.throws(() => materializeValidatedPlans([{ id: "e1", clusterId: "g-aaa", provisionalIntent: "x", provisionalSources: ["s1", "s2"] }, { id: "e1", clusterId: "g-aaa", provisionalIntent: "y", provisionalSources: ["s1", "s2"] }], { stateDir }), /duplicate/);
  });

  it("keeps mock behavior with no synthetic provenance/fallback candidate", async () => {
    const { synthesizeCandidates } = await import("../src/synthesize.js");
    const empty = { version: 1, minGapEvidence: 2, clusters: [] };
    const plans = synthesizeCandidates(empty, { evidenceIndex: new Map() });
    assert.deepEqual(plans, []);
    const src = fs.readFileSync(new URL("../src/synthesize.js", import.meta.url), "utf8");
    assert.ok(!src.includes("exp-fallback-open-gap"), "no synthetic fallback candidate");
  });
});

describe("central minGapEvidence floor (CLI and API boundaries match)", () => {
  it("assertMinGapEvidence accepts integers >=2 and rejects others", () => {
    assert.equal(assertMinGapEvidence(2), 2);
    assert.equal(assertMinGapEvidence("3"), 3);
    for (const bad of [0, 1, 1.5, "x", null, undefined, NaN]) {
      assert.throws(() => assertMinGapEvidence(bad), /integer >= 2/);
    }
  });

  it("runPipeline rejects invalid floor fail-closed", async () => {
    const { runPipeline } = await import("../src/pipeline.js");
    const home = fs.mkdtempSync(path.join(os.tmpdir(), "ca-home-"));
    const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-state-"));
    await assert.rejects(() => runPipeline({ home, stateDir, minGapEvidence: 1 }), /integer >= 2/);
  });

  it("runSynthesizeResume rejects invalid floor fail-closed (matches run)", async () => {
    const { runSynthesizeResume } = await import("../src/synthesize-resume.js");
    const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-state-"));
    await assert.rejects(() => runSynthesizeResume({ stateDir, minGapEvidence: 1 }), /integer >= 2/);
  });
});

describe("regression: normal production run wires prepared workspace root to materialization", () => {
  it("valid stdout through runPipeline yields measured artifact (no silent drop)", async () => {
    const { runPipeline } = await import("../src/pipeline.js");
    const home = fs.mkdtempSync(path.join(os.tmpdir(), "ca-reg-home-"));
    const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-reg-state-"));
    const dir = path.join(home, ".codex", "sessions");
    fs.mkdirSync(dir, { recursive: true });
    const gap = (quote) => ({
      proposedInstruction: quote,
      mistake: quote,
      quote,
      recurrenceRisk: "every session pays",
    });
    const QUOTE = "sessions re-derive project context from scratch";
    const QUOTE_B = "sessions never record why a fix was chosen";
    const gapEvidence = () => ({ status: "ok", positive: [], negative: [], gaps: [gap(QUOTE), gap(QUOTE_B)] });
    for (let i = 0; i < 2; i += 1) {
      const payload = JSON.stringify({ role: "user", text: `bootstrap context please ${i}` });
      const tools = ["read", "search", "test"].map((name) => JSON.stringify({ kind: "tool", name }));
      fs.writeFileSync(path.join(dir, `2026-01-0${i + 1}T00-00-00Z.jsonl`), `${[payload, ...tools].join("\n")}\n`, "utf8");
    }
    const proposal = await runPipeline({
      home,
      stateDir,
      analyzer: "acpx",
      runId: "run-REG1",
      analyzeInvoke: () => ({ status: "ok", evidence: gapEvidence() }),
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
      synthesizeInvoke: (args) => {
        assert.equal(args?.workspace, undefined, "text-only invoke must not receive workspace");
        assert.equal(args?.cwd, undefined, "text-only invoke must not receive cwd");
        const ledger = args?.ledger;
        const cluster = (ledger?.clusters || []).find((c) => c.eligible);
        assert.ok(cluster, "ledger must hold an eligible cluster");
        return {
          status: "ok",
          plans: [{ clusterId: cluster.id, provisionalIntent: cluster.proposedInstruction, provisionalSources: [...cluster.sources] }],
        };
      },
      annotateInvoke: (args) => {
        if (args?.stage === "annotate-preface") return { status: "ok", ready: true };
        const staged = args?.staged || [];
        const ledger = args?.ledger;
        return {
          status: "ok",
          annotations: staged.map((pl, i) => {
            const cluster = (ledger?.clusters || []).find((c) => String(c.id) === String(pl.clusterId));
            const quote = String(cluster?.representativeQuote || QUOTE);
            return {
              id: pl.id || `e${i + 1}`,
              verdict: "keep",
              reason: String(pl.provisionalIntent || "keep"),
              record: {
                id: `exp-reg-a1b2c3d4e5f${i}`,
                title: String(pl.provisionalIntent),
                body: `Recurring gap: ${pl.provisionalIntent}`,
                clusterId: String(pl.clusterId),
                sources: [...pl.provisionalSources],
                evidence: pl.provisionalSources.map((source) => ({ polarity: "negative", text: quote, source, effect: quote })),
                counterevidence: "none observed",
                compilerImplication: "compiler appends this record to the experience block",
              },
            };
          }),
        };
      },
    });
    assert.ok(proposal.edits.length >= 1, "valid stdout must yield candidate edits through the normal run path");
    const measured = JSON.parse(fs.readFileSync(path.join(stateDir, "measured-changes.json"), "utf8"));
    const changes = measured.changes || measured;
    assert.ok(changes.length >= 1, "measured artifact must exist (materialization hit the measured workspace)");
    const wsFiles = fs.readdirSync(path.join(stateDir, "synthesis-workspace")).filter((n) => n.endsWith(".md"));
    assert.ok(wsFiles.length >= 1, "materialized markdown must live under the prepared workspace root");
    const stagedIds = new Set((changes || []).map((m) => String(m.recordId || "")));
    for (const edit of proposal.edits) {
      assert.ok(stagedIds.has(String(edit.id)), `final edit ${edit.id} must bind a measured artifact`);
    }
  });

  it("pipeline passes its prepared workspace root to synthesis materialization", () => {
    const src = fs.readFileSync(new URL("../src/pipeline.js", import.meta.url), "utf8");
    assert.ok(/synthesizeWithAcpx\(ledger,\s*\{[\s\S]*?workspaceRoot:\s*workspaceCwd[\s\S]*?\}\);/.test(src), "pipeline must pass workspaceRoot: workspaceCwd to synthesizeWithAcpx");
  });
});
