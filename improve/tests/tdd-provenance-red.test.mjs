import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SYNTH_MD = path.join(HERE, "..", "prompts", "synthesis.md");

function tmpDir(prefix = "ca-prov-red-") {
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

function validFrontmatterBody() {
  return `---\nclusterId: g-aaa\nprovisionalSources:\n  - s1\n  - s2\n---\n# Bootstrap context once\n\nsessions re-derive project context from scratch\n`;
}

describe("TDD: synthesis prompt is text-only with a strict JSON plans contract", () => {
  it("checked-in synthesis.md is text-only and contracts the plans payload", () => {
    const text = fs.readFileSync(SYNTH_MD, "utf8");
    assert.ok(/text-only/i.test(text), "synthesis prompt must declare text-only proposer");
    assert.ok(!/edit-only|edit turn/i.test(text), "synthesis prompt must not describe an edit turn");
    assert.ok(!/inspect and edit ONLY/i.test(text), "synthesis prompt must never ask to inspect/edit workspace");
    assert.ok(/clusterId/.test(text), "synthesis prompt must mandate clusterId provenance");
    assert.ok(/provisionalSources/.test(text), "synthesis prompt must mandate provisionalSources provenance");
    assert.ok(/provisionalIntent/.test(text), "synthesis prompt must contract provisionalIntent");
    assert.ok(/"plans"/.test(text), "synthesis prompt must contract a plans JSON key");
  });
});

describe("TDD RED: valid workspace frontmatter provenance reaches annotation", () => {
  it("parses clusterId + provisionalSources (>=2 distinct) from the actual changed file, stable measured ID, diff + eligible quote context reach annotation", async () => {
    const { prepareExperienceWorkspace, measureExperienceWorkspace } = await import("../src/experience-workspace.js");
    const { default: synthesizeMod } = await import("../src/synthesize.js").catch(() => ({ default: null }));
    void synthesizeMod;
    const stateDir = tmpDir();
    const ws = prepareExperienceWorkspace({ stateDir, records: [] });
    const filePath = path.join(ws.root, "e1.md");
    fs.writeFileSync(filePath, validFrontmatterBody(), "utf8");
    const first = measureExperienceWorkspace(ws);
    const second = measureExperienceWorkspace(ws);
    const m1 = first.find((m) => String(m.file || "").includes("e1.md"));
    assert.ok(m1, "changed file e1.md must be measured");
    // Provenance parsed from the actual file frontmatter.
    assert.equal(m1.clusterId, "g-aaa", "measured change must carry clusterId parsed from file frontmatter");
    assert.deepEqual([...new Set(m1.provisionalSources || m1.sources || [])].sort(), ["s1", "s2"]);
    // Stable measured ID across re-measurement.
    const m1Again = second.find((m) => String(m.file || "").includes("e1.md"));
    assert.ok(m1Again, "second measurement must still observe e1.md");
    assert.equal(m1Again.id, m1.id, "measured ID must be stable across measurements");
    // Exact diff / eligible quote context travels with the measurement.
    const diffText = String(m1.diff || m1.text || "");
    assert.ok(
      diffText.includes("sessions re-derive project context from scratch"),
      "measured diff/text must carry the exact eligible quote from the file body",
    );
    assert.ok(
      Array.isArray(m1.eligibleSources || m1.provisionalSources) && (m1.eligibleSources || m1.provisionalSources).length >= 2,
      "measurement must carry >=2 distinct eligible/provisional sources",
    );
    // Reaches annotation along with that context.
    const { annotateStaging } = await import("../src/annotate.js");
    const plan = {
      id: "e1",
      kind: "add",
      clusterId: "g-aaa",
      provisionalIntent: "Bootstrap context once",
      provisionalSources: ["s1", "s2"],
      provisionalCount: 2,
    };
    const out = await annotateStaging([plan], {
      stateDir: tmpDir(),
      ledger: ledger(),
      evidenceIndex: evidenceIndex(),
      measuredChanges: first,
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        // Annotation must have received the measured diff + eligible quote context.
        const ctx = JSON.stringify(args);
        assert.ok(ctx.includes("m1") || ctx.includes("e1.md") || ctx.includes("sessions re-derive project context from scratch"), "annotate invoke must receive measured diff/quote context");
        return {
          status: "ok",
          annotations: [
            {
              id: "e1",
              verdict: "keep",
              reason: "sessions re-derive project context from scratch",
              record: {
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
              },
            },
          ],
        };
      },
    });
    assert.equal(out.failed, false);
    const annotated = (out.annotated || [])[0];
    assert.ok(annotated, "valid frontmatter change must reach annotation");
    assert.deepEqual(annotated.measuredIds, [m1.id], "annotation must bind the stable measured ID");
  });
});

describe("TDD RED: malformed/missing provenance rejects only that change", () => {
  it("rejects the individual malformed change while the valid sibling remains", async () => {
    const { prepareExperienceWorkspace, measureExperienceWorkspace } = await import("../src/experience-workspace.js");
    const { annotateStaging } = await import("../src/annotate.js");
    const stateDir = tmpDir();
    const ws = prepareExperienceWorkspace({ stateDir, records: [] });
    fs.writeFileSync(path.join(ws.root, "e1.md"), validFrontmatterBody(), "utf8");
    // Malformed sibling: broken YAML + missing clusterId.
    fs.writeFileSync(path.join(ws.root, "e2.md"), `---\nclusterId: [unclosed\nprovisionalSources: s1\n---\nbody without provenance\n`, "utf8");
    const measured = measureExperienceWorkspace(ws);
    const mValid = measured.find((m) => String(m.file || "").includes("e1.md"));
    const mBad = measured.find((m) => String(m.file || "").includes("e2.md"));
    assert.ok(mValid, "valid sibling must be measured");
    assert.ok(mBad, "malformed sibling must still be measured (to be individually rejected)");
    const plans = [
      { id: "e1", kind: "add", clusterId: "g-aaa", provisionalIntent: "Bootstrap context once", provisionalSources: ["s1", "s2"], provisionalCount: 2 },
      { id: "e2", kind: "add", clusterId: "g-aaa", provisionalIntent: "Bootstrap context once", provisionalSources: ["s1", "s2"], provisionalCount: 2 },
    ];
    const goodRecord = {
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
            { id: "e1", verdict: "keep", reason: "m", record: goodRecord },
            // Malformed provenance keep attempt must be individually rejected, not take down the sibling.
            { id: "e2", verdict: "keep", reason: "m", record: { ...goodRecord, id: "exp-bad", clusterId: "", sources: [] } },
          ],
        };
      },
    });
    const keptIds = (out.annotated || out.edits || []).map((a) => a.id || a.candidateId);
    assert.ok(keptIds.includes("e1"), "valid sibling must survive when malformed sibling is rejected");
    assert.ok(!keptIds.includes("e2"), "malformed/missing provenance change must be individually rejected");
  });
});

describe("TDD RED: no automatic/cyclic cluster association", () => {
  it("absent explicit provenance yields no cluster linkage and no cyclic self-association", async () => {
    const { prepareExperienceWorkspace, measureExperienceWorkspace } = await import("../src/experience-workspace.js");
    const { annotateStaging } = await import("../src/annotate.js");
    const stateDir = tmpDir();
    const ws = prepareExperienceWorkspace({ stateDir, records: [] });
    // No frontmatter at all: must not be auto-associated to any cluster.
    fs.writeFileSync(path.join(ws.root, "orphan.md"), `# Orphan\n\nsessions re-derive project context from scratch\n`, "utf8");
    const measured = measureExperienceWorkspace(ws);
    const orphan = measured.find((m) => String(m.file || "").includes("orphan.md"));
    assert.ok(orphan, "orphan file must be measured");
    assert.equal(orphan.clusterId ?? null, null, "absent explicit provenance must not auto-associate a clusterId");
    assert.ok(
      !orphan.provisionalSources && !orphan.sources,
      "absent explicit provenance must not invent provisional/sources linkage",
    );
    // Cyclic check: orphan must not reference its own measured ID as a source/cluster and
    // must not be linked back to itself via cluster association.
    const blob = JSON.stringify(orphan);
    assert.ok(!blob.includes(orphan.id + ":") && !/g-aaa/.test(blob), "orphan measurement must carry no cyclic cluster association");
    // Annotation must not auto-associate the orphan: a keep claiming g-aaa with no
    // explicit file provenance must not survive to annotated/finals.
    const out = await annotateStaging(
      [{ id: "orphan", kind: "add", clusterId: "g-aaa", provisionalIntent: "Bootstrap context once", provisionalSources: ["s1", "s2"], provisionalCount: 2 }],
      {
        stateDir: tmpDir(),
        ledger: ledger(),
        evidenceIndex: evidenceIndex(),
        measuredChanges: measured,
        invoke: (args) => {
          if (args.stage === "annotate-preface") return { status: "ok", ready: true };
          return {
            status: "ok",
            annotations: [
              {
                id: "orphan",
                verdict: "keep",
                reason: "m",
                record: {
                  id: "exp-orphan",
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
                },
              },
            ],
          };
        },
      },
    );
    const survived = (out.annotated || out.edits || []).filter((a) => (a.id || a.candidateId) === "orphan");
    assert.equal(survived.length, 0, "orphan with no explicit file provenance must not auto-associate to g-aaa at annotation");
  });
});
