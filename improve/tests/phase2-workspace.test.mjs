import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { prepareExperienceWorkspace, measureExperienceWorkspace, assertSynthesisContainment } from "../src/experience-workspace.js";
import { consolidateLedger, loadOpenGaps } from "../src/consolidate.js";
import { acpxSynthesisInvoke, synthesizeWithAcpx } from "../src/synthesize.js";
import { runAcpxPromptFile } from "../src/acpx-text.js";

function tmpDir() { return fs.mkdtempSync(path.join(os.tmpdir(), "ca-phase2-")); }

describe("phase2 workspace measurement", () => {
  it("measures created/modified/deleted markdown with stable anchored diffs", () => {
    const stateDir = tmpDir();
    const ws = prepareExperienceWorkspace({ stateDir, records: [
      { id: "keep", text: "baseline" },
      { id: "gone", text: "bye" },
    ]});
    fs.writeFileSync(path.join(ws.root, "keep.md"), "baseline\namended\n", "utf8");
    fs.rmSync(path.join(ws.root, "gone.md"), { force: true });
    fs.writeFileSync(path.join(ws.root, "fresh.md"), "# fresh\n\nnew\n", "utf8");
    const measured = measureExperienceWorkspace(ws);
    const kinds = new Set(measured.map((m) => m.kind));
    assert.ok(kinds.has("created") && kinds.has("modified") && kinds.has("deleted"));
    for (const m of measured) {
      assert.ok(String(m.path).endsWith(".md"));
      assert.ok(String(m.diff).trim().length > 0);
      assert.ok(String(m.diff).includes(String(m.id)));
    }
  });
  it("refuses durable writes outside the private workspace", () => {
    assert.throws(() => assertSynthesisContainment("workspaces/alignment/artifacts/SOUL.md", "/tmp/ws"), /refused|forbidden/);
    assert.throws(() => assertSynthesisContainment("/repo/file.md", "/tmp/ws"), /denied|refused|forbidden/);
  });
});

describe("phase2 open-gap persistence", () => {
  it("persists open gaps and corroborates singletons before the floor", () => {
    const stateDir = tmpDir();
    const singleton = (id, src) => ({ id, proposedInstruction: "bootstrap once", representativeQuote: "bootstrap context once", mistake: "bootstrap context once", sources: [src], count: 1, eligible: false, perSource: { [src]: { quote: "bootstrap context once", mistake: "m" } } });
    const first = { version: 1, minGapEvidence: 2, clusters: [singleton("g-a", "s1")] };
    const r1 = consolidateLedger(first, { analyzer: "mock", stateDir, minGapEvidence: 2 });
    const persisted = loadOpenGaps(stateDir);
    assert.ok(persisted.gaps.length >= 1);
    const second = { version: 1, minGapEvidence: 2, clusters: [{ ...singleton("g-a", "s2"), sources: ["s2"] }] };
    // Same stable id, new source: union reaches the floor before eligibility filtering.
    const r2 = consolidateLedger(second, { analyzer: "mock", stateDir, minGapEvidence: 2 });
    const merged = r2.ledger.clusters.find((c) => c.id === "g-a");
    assert.ok(merged && merged.eligible && merged.corroboratedOpenGap);
  });
});

describe("phase2 acpx workspace cwd", () => {
  it("threads explicit workspace cwd without breaking existing callers", () => {
    const stateDir = tmpDir();
    const ws = prepareExperienceWorkspace({ stateDir, records: [] });
    let seen = null;
    const ledger = { version: 1, minGapEvidence: 2, clusters: [{ id: "g-1", proposedInstruction: "do x", representativeQuote: "q", mistake: "m", sources: ["s1", "s2"], count: 2, eligible: true, perSource: { s1: { quote: "q", mistake: "m" }, s2: { quote: "q", mistake: "m" } } }] };
    const out = synthesizeWithAcpx(ledger, {
      evidenceIndex: new Map([["s1", [{ quote: "q" }]], ["s2", [{ quote: "q" }]]]),
      invoke: (args) => {
        seen = args;
        // EDIT-ONLY edit turn: the production process authors the workspace cwd.
        fs.writeFileSync(path.join(String(args?.workspace || ws.root), "e1.md"), "---\nclusterId: g-1\nprovisionalSources:\n  - s1\n  - s2\n---\n# do x\n\nbody q\n", "utf8");
        return { status: "ok", plans: [{ id: "e1", clusterId: "g-1", provisionalIntent: "do x", provisionalSources: ["s1", "s2"] }] };
      },
      stateDir, runId: "run-WS1", workspace: ws.root, cwd: ws.root,
    });
    assert.equal(out.edits.length, 1);
    assert.equal(out.edits[0].id, "e1");
    assert.ok(seen && (seen.workspace === ws.root || seen.cwd === ws.root));
    // Existing caller without workspace stays compatible: fail-closed with no edits (never throws).
    const freshState = tmpDir();
    const out2 = synthesizeWithAcpx(ledger, {
      evidenceIndex: new Map(),
      invoke: () => ({ status: "ok", plans: [{ clusterId: "g-1", provisionalIntent: "do x", provisionalSources: ["s1", "s2"] }] }),
      stateDir: freshState, runId: "run-WS2",
    });
    assert.deepEqual(out2.edits, []);
    void runAcpxPromptFile;
    void acpxSynthesisInvoke;
  });
});
