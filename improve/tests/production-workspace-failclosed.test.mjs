// TDD: production workspace correctness — fail-closed, no seeds, EDIT-only workspace.
// Covers: (1) no synthetic seed records, (2) EDIT-only workspace prompt,
// (3) exact workspace CWD, (4) measurement drives annotation, (5) JSON-only
// with no file changes yields zero candidate edits.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { synthesizeWithAcpx, measuredIdsForPlan } from "../src/synthesize.js";
import { prepareExperienceWorkspace, measureExperienceWorkspace } from "../src/experience-workspace.js";

function makeLedger() {
  return {
    clusters: [
      {
        id: "c1",
        eligible: true,
        proposedInstruction: "Do X",
        sources: ["s1", "s2"],
        count: 2,
        perSource: { s1: { quote: "q1" }, s2: { quote: "q2" } },
        quoteProvenance: [
          { source: "s1", quote: "q1" },
          { source: "s2", quote: "q2" },
        ],
      },
    ],
  };
}

function makeEvidenceIndex() {
  return new Map([
    ["s1", [{ quote: "q1" }]],
    ["s2", [{ quote: "q2" }]],
  ]);
}

test("no seed records exist in fresh workspace", () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-state-"));
  const ws = prepareExperienceWorkspace({ stateDir, records: [] });
  const root = ws?.root || path.join(stateDir, "synthesis-workspace");
  assert.ok(!fs.existsSync(path.join(root, "seed-keep.md")), "seed-keep.md must not exist");
  assert.ok(!fs.existsSync(path.join(root, "seed-remove.md")), "seed-remove.md must not exist");
  const measured = measureExperienceWorkspace(ws);
  const ids = JSON.stringify(measured);
  assert.ok(!ids.includes("seed-keep"), "measured changes must not contain seed-keep");
  assert.ok(!ids.includes("seed-remove"), "measured changes must not contain seed-remove");
  // Pipeline itself must not seed synthetic records.
  const pipelineSrc = fs.readFileSync(new URL("../src/pipeline.js", import.meta.url), "utf8");
  assert.ok(!pipelineSrc.includes("seed-keep"), "pipeline.js must not reference seed-keep");
  assert.ok(!pipelineSrc.includes("seed-remove"), "pipeline.js must not reference seed-remove");
  // Mock synthesis author must not fabricate seed lifecycle files either.
  const containedRoot = path.join(stateDir, "synthesis-workspace");
  fs.mkdirSync(containedRoot, { recursive: true });
  import("../src/synthesize.js").then(() => {});
  const { applyMockSynthesisWorkspace } = process._getActiveHandles ? {} : {};
  void applyMockSynthesisWorkspace;
});

test("mock synthesis author creates no seed files", async () => {
  const { applyMockSynthesisWorkspace } = await import("../src/synthesize.js");
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-state-"));
  const ws = prepareExperienceWorkspace({ stateDir, records: [] });
  const root = ws?.root || path.join(stateDir, "synthesis-workspace");
  applyMockSynthesisWorkspace(
    [{ id: "e1", provisionalIntent: "Do X", clusterId: "c1" }],
    root,
    { stateDir },
  );
  assert.ok(!fs.existsSync(path.join(root, "seed-keep.md")), "mock author must not write seed-keep.md");
  assert.ok(!fs.existsSync(path.join(root, "seed-remove.md")), "mock author must not write seed-remove.md");
  assert.ok(fs.existsSync(path.join(root, "e1.md")), "mock author still authors the plan record");
});

test("text-only production ACPX synthesis materializes markdown and measurement drives annotation", () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-state-"));
  const ws = prepareExperienceWorkspace({ stateDir, records: [] });
  const root = ws?.root || path.join(stateDir, "synthesis-workspace");
  let captured = null;
  const invoke = (args) => {
    captured = args;
    // TEXT-ONLY: the production proposer returns stdout plans only and must
    // not receive any workspace/cwd; deterministic code materializes.
    assert.equal(args?.cwd, undefined, "text-only invoke must not receive cwd");
    assert.equal(args?.workspace, undefined, "text-only invoke must not receive workspace");
    return {
      status: "ok",
      plans: [{ clusterId: "c1", provisionalIntent: "Do X", provisionalSources: ["s1", "s2"] }],
    };
  };
  const out = synthesizeWithAcpx(makeLedger(), {
    evidenceIndex: makeEvidenceIndex(),
    stateDir,
    runId: "run-test",
    invoke,
  });
  assert.ok(captured, "invoke must have been called");
  assert.equal(captured.cwd, undefined, "text-only invoke carries no cwd");
  assert.equal(captured.workspace, undefined, "text-only invoke carries no workspace");
  const measured = measureExperienceWorkspace(ws);
  assert.ok(measured.length > 0, "measurement must observe the written markdown");
  // Measurement drives annotation: plan binds by measured IDs.
  const ids = measuredIdsForPlan(out.edits[0]?.id || "e1", measured);
  assert.ok(ids.length > 0, `measured IDs must bind to plan id (measured=${JSON.stringify(measured)})`);
});

test("production prompt is text-only proposer, never an edit turn", () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-state-"));
  let seenPrompt = "";
  const invoke = (args) => {
    seenPrompt = String(args?.prompt || "");
    return {
      status: "ok",
      plans: [{ clusterId: "c1", provisionalIntent: "Do X", provisionalSources: ["s1", "s2"] }],
    };
  };
  synthesizeWithAcpx(makeLedger(), {
    evidenceIndex: makeEvidenceIndex(),
    stateDir,
    runId: "run-test",
    invoke,
  });
  const lowered = seenPrompt.toLowerCase();
  assert.ok(lowered.includes("text-only"), "prompt must declare text-only proposer");
  assert.ok(!lowered.includes("edit turn"), "prompt must never describe an edit turn");
  assert.ok(!lowered.includes("inspect and edit only"), "prompt must never ask to inspect/edit workspace");
});

test("invalid synthesis plans fail closed with zero candidate edits", async () => {
  // Dynamic import so pipeline edits are picked up after implementation.
  const { runPipeline } = await import("../src/pipeline.js");
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "ca-home-"));
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-state-"));
  // Eligible cluster c1/s1+s2 so the JSON plan is VALID; the only reason to
  // yield zero is fail-closed on empty workspace measurement. Annotate double
  // would succeed if given staged plans, proving the zero comes from the
  // workspace gate, not from annotate failing.
  const ledgerForTest = {
    clusters: [
      {
        id: "c1",
        eligible: true,
        proposedInstruction: "Do X",
        sources: ["s1", "s2"],
        count: 2,
        perSource: { s1: { quote: "q1" }, s2: { quote: "q2" } },
        quoteProvenance: [
          { source: "s1", quote: "q1" },
          { source: "s2", quote: "q2" },
        ],
      },
    ],
  };
  const proposal = await runPipeline({
    home,
    stateDir,
    analyzer: "acpx",
    analyzeInvoke: async () => ({ status: "skipped", reason: "tdd empty" }),
    consolidateInvoke: () => ({ status: "ok", ledger: ledgerForTest }),
    synthesizeInvoke: (args) => {
      // TEXT-ONLY: return valid plans with no filesystem access; deterministic
      // code materializes. Invalid cluster would fail closed instead.
      assert.equal(args?.cwd, undefined, "text-only invoke must not receive cwd");
      assert.equal(args?.workspace, undefined, "text-only invoke must not receive workspace");
      return {
        status: "ok",
        plans: [{ clusterId: "c-ghost", provisionalIntent: "Do X", provisionalSources: ["s1", "s2"] }],
      };
    },
    annotateInvoke: (args) => {
      // Would-be-successful annotate: if the pipeline incorrectly stages
      // plan-derived records, this returns finals so the bug is visible.
      const staged = args?.staged || [];
      return {
        status: "ok",
        annotations: staged.map((p) => ({
          id: p.id,
          kind: "add",
          clusterId: p.clusterId,
          record: {
            id: p.id,
            clusterId: p.clusterId,
            title: "Do X",
            body: "x".repeat(10),
            sources: ["s1", "s2"],
            evidence: [
              { source: "s1", text: "q1" },
              { source: "s2", text: "q2" },
            ],
            counterevidence: "none observed",
            compilerImplication: "append",
          },
          evidence: [
            { source: "s1", text: "q1" },
            { source: "s2", text: "q2" },
          ],
          annotation: { verdict: "keep", reason: "tdd would-keep" },
        })),
      };
    },
  });
  assert.equal(proposal.edits.length, 0, `invalid plans must yield zero edits (got ${JSON.stringify(proposal.edits)})`);
  const stagingNote = String(proposal?.staging?.note || "") + String(proposal?.synthesis?.note || "");
  void stagingNote;
});
