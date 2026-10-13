import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

function tmpDir(prefix = "ca-prov-bridge-") {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
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
    ],
  };
}

function evidenceIndex() {
  return new Map([
    ["s1", [{ quote: "sessions re-derive project context from scratch", effect: "e1" }]],
    ["s2", [{ quote: "sessions re-derive project context from scratch", effect: "e2" }]],
  ]);
}

function goodRecord() {
  return {
    id: "exp-bootstrap-a1b2c3d4e5f6",
    title: "Bootstrap context once",
    body: "Recurring gap seen in 2 session(s): sessions re-derive project context from scratch",
    sources: ["s1", "s2"],
    clusterId: "g-aaa",
    evidence: [
      { polarity: "negative", text: "sessions re-derive project context from scratch", source: "s1", effect: "m" },
      { polarity: "negative", text: "sessions re-derive project context from scratch", source: "s2", effect: "m" },
    ],
    counterevidence: "none observed",
    compilerImplication: "compiler appends this record to the experience block",
  };
}

describe("provenance bridge: centralized YAML frontmatter parser (sequence forms)", () => {
  it("parses block sequence, flow sequence, and quoted variants identically", async () => {
    const mod = await import("../src/workspace-frontmatter.js");
    assert.ok(typeof mod.parseWorkspaceFrontmatter === "function", "shared parser must exist");
    const bodies = [
      `---\nclusterId: g-aaa\nprovisionalSources:\n  - s1\n  - s2\n---\n# T\n\nsessions re-derive project context from scratch\n`,
      `---\nclusterId: g-aaa\nprovisionalSources: ["s1", "s2"]\n---\n# T\n\nsessions re-derive project context from scratch\n`,
      `---\nclusterId: "g-aaa"\nprovisionalSources:\n  - "s1"\n  - 's2'\n---\n# T\n\nsessions re-derive project context from scratch\n`,
      `---\nclusterId: g-aaa # eligible cluster\nprovisionalSources: [s1, s2]\n---\n# T\n\nsessions re-derive project context from scratch\n`,
    ];
    for (const body of bodies) {
      const parsed = mod.parseWorkspaceFrontmatter(body);
      assert.equal(parsed.parseError, null, `should parse: ${body.slice(0, 60)}`);
      assert.equal(parsed.clusterId, "g-aaa");
      assert.deepEqual([...parsed.provisionalSources].sort(), ["s1", "s2"]);
    }
    // Malformed stays unlinked, never throws.
    const bad = mod.parseWorkspaceFrontmatter(`---\nclusterId: [unclosed\nprovisionalSources: s1\n---\nbody\n`);
    assert.ok(bad.parseError, "malformed YAML must report parseError");
    assert.equal(bad.clusterId, null);
  });

  it("synthesize and measurement share one parser implementation", async () => {
    const src = fs.readFileSync(new URL("../src/synthesize.js", import.meta.url), "utf8");
    assert.ok(src.includes("workspace-frontmatter.js"), "synthesize must import the shared parser");
    const wsSrc = fs.readFileSync(new URL("../src/experience-workspace.js", import.meta.url), "utf8");
    assert.ok(wsSrc.includes("workspace-frontmatter.js"), "experience-workspace must use the shared parser");
    assert.ok(!/function parseWorkspaceFileProvenance\(text\)/.test(src), "synthesize must not keep a duplicated subset parser");
  });

  it("flow-sequence frontmatter on the actual changed file measures with provenance", async () => {
    const { prepareExperienceWorkspace, measureExperienceWorkspace } = await import("../src/experience-workspace.js");
    const stateDir = tmpDir();
    const ws = prepareExperienceWorkspace({ stateDir, records: [] });
    fs.writeFileSync(
      path.join(ws.root, "e1.md"),
      `---\nclusterId: g-aaa\nprovisionalSources: ["s1", "s2"]\n---\n# Bootstrap context once\n\nsessions re-derive project context from scratch\n`,
      "utf8",
    );
    const measured = measureExperienceWorkspace(ws);
    const m1 = measured.find((m) => String(m.file || "").includes("e1.md"));
    assert.ok(m1, "flow-sequence file must be measured");
    assert.equal(m1.clusterId, "g-aaa");
    assert.deepEqual([...new Set(m1.provisionalSources || [])].sort(), ["s1", "s2"]);
  });
});

describe("provenance bridge: unmatched candidate with workspace measurement is rejected individually", () => {
  it("ghost plan with no measured file is rejected while the valid sibling keeps its stable measured ID", async () => {
    const { prepareExperienceWorkspace, measureExperienceWorkspace } = await import("../src/experience-workspace.js");
    const { annotateStaging } = await import("../src/annotate.js");
    const stateDir = tmpDir();
    const ws = prepareExperienceWorkspace({ stateDir, records: [] });
    fs.writeFileSync(
      path.join(ws.root, "e1.md"),
      `---\nclusterId: g-aaa\nprovisionalSources:\n  - s1\n  - s2\n---\n# Bootstrap context once\n\nsessions re-derive project context from scratch\n`,
      "utf8",
    );
    const measured = measureExperienceWorkspace(ws);
    const m1 = measured.find((m) => String(m.file || "").includes("e1.md"));
    assert.ok(m1, "valid file must be measured");
    const plans = [
      { id: "e1", kind: "add", clusterId: "g-aaa", provisionalIntent: "Bootstrap context once", provisionalSources: ["s1", "s2"], provisionalCount: 2 },
      { id: "ghost", kind: "add", clusterId: "g-aaa", provisionalIntent: "Bootstrap context once", provisionalSources: ["s1", "s2"], provisionalCount: 2 },
    ];
    const out = await annotateStaging(plans, {
      stateDir: tmpDir(),
      ledger: ledger(),
      evidenceIndex: evidenceIndex(),
      measuredChanges: measured,
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return {
          status: "ok",
          annotations: [
            { id: "e1", verdict: "keep", reason: "m", record: goodRecord() },
            { id: "ghost", verdict: "keep", reason: "m", record: { ...goodRecord(), id: "exp-ghost" } },
          ],
        };
      },
    });
    assert.equal(out.failed, false);
    const keptIds = (out.annotated || []).map((a) => a.id || a.candidateId);
    assert.ok(keptIds.includes("e1"), "valid sibling must survive");
    assert.ok(!keptIds.includes("ghost"), "unmatched candidate with no measured provenance must be individually rejected");
    const kept = (out.annotated || []).find((a) => (a.id || a.candidateId) === "e1");
    assert.deepEqual(kept.measuredIds, [m1.id], "survivor must bind the stable measured ID (not a name-only fallback)");
    assert.ok(!("measuredIds" in ((out.annotated || []).find((a) => (a.id || a.candidateId) === "ghost") || {})), "rejected ghost must not leak");
  });
});
