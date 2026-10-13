import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(HERE, "..", "src");

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "ca-stage-annotate-"));
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

function changePlan(overrides = {}) {
  return {
    id: "e1",
    kind: "add",
    clusterId: "g-aaa",
    provisionalIntent: "Bootstrap context once",
    provisionalSources: ["s1", "s2"],
    provisionalCount: 2,
    ...overrides,
  };
}

function finalRecord(overrides = {}) {
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
    ...overrides,
  };
}

function annotationKeep(overrides = {}) {
  return {
    id: "e1",
    verdict: "keep",
    reason: "sessions re-derive project context from scratch",
    record: finalRecord(),
    ...overrides,
  };
}

async function loadStage() {
  return import("../src/stage.js");
}

async function loadAnnotate() {
  return import("../src/annotate.js");
}

async function loadMeasure() {
  return import("../src/measure.js");
}

describe("synth->private stage / measure->annotate-preface->annotate (annotation ownership)", () => {
  it("preface precedes annotate with sentinel first", async () => {
    const annotate = await loadAnnotate();
    assert.equal(typeof annotate.renderAnnotatePreface, "function");
    assert.equal(typeof annotate.annotateStaging, "function");
    const calls = [];
    const stateDir = tmpDir();
    const preface = annotate.renderAnnotatePreface(changePlan(), { stateDir });
    assert.ok(String(preface).startsWith("<!-- ca-improve:self-session -->\n"));
    await annotate.annotateStaging([changePlan()], {
      stateDir,
      ledger: ledger(),
      evidenceIndex: evidenceIndex(),
      invoke: (args) => {
        calls.push(args.stage);
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "ok", annotations: [annotationKeep()] };
      },
    });
    assert.deepEqual(calls, ["annotate-preface", "annotate"]);
  });

  it("synthesis plans carry no final record; annotation is the sole full-record origin", async () => {
    const { synthesizeCandidates } = await import("../src/synthesize.js");
    const plans = synthesizeCandidates(ledger(), { evidenceIndex: evidenceIndex() });
    assert.equal(plans.length, 1);
    for (const forbidden of ["record", "evidence", "title", "body", "counterevidence", "compilerImplication", "stagedArtifact", "diff"]) {
      assert.equal(plans[0][forbidden], undefined, `synth plan must not carry ${forbidden}`);
    }
    // Staging strips any leaked final fields so no synth final record applies.
    const stage = await loadStage();
    const leaked = { ...changePlan(), record: finalRecord(), evidence: finalRecord().evidence, title: "leaked" };
    const staged = stage.stageCandidates([leaked], { stateDir: tmpDir(), runId: "run-STRIP1" });
    assert.equal(staged[0].record, undefined);
    assert.equal(staged[0].evidence, undefined);
    assert.equal(staged[0].title, undefined);
    assert.equal(staged[0].clusterId, "g-aaa");
  });

  it("unannotated staged plans cannot reach apply/final proposal", async () => {
    const stage = await loadStage();
    assert.equal(typeof stage.stageCandidates, "function");
    assert.equal(typeof stage.buildFinalProposal, "function");
    const stateDir = tmpDir();
    const staged = stage.stageCandidates([changePlan()], { stateDir, runId: "run-STAGE1" });
    assert.ok(staged && staged.length === 1);
    assert.throws(() => stage.buildFinalProposal(staged, { stateDir, ledger: ledger(), evidenceIndex: evidenceIndex() }), /annotat/i);
  });

  it("no synth final record applies: final proposal requires annotation finals", async () => {
    const stage = await loadStage();
    const stateDir = tmpDir();
    // A staged plan plus a synth-shaped record (no annotation) must not build.
    const synthShaped = { ...changePlan(), record: finalRecord(), stagedArtifact: "x", diff: "y" };
    assert.throws(() => stage.buildFinalProposal([synthShaped], { stateDir, ledger: ledger(), evidenceIndex: evidenceIndex() }), /annotat|sole full-record/i);
    // An annotated keep builds a final with the annotation record only.
    const annotated = [{ ...changePlan(), annotation: { verdict: "keep", reason: "m", record: finalRecord() }, finalRecord: finalRecord() }];
    const finals = stage.buildFinalProposal(annotated, { stateDir, ledger: ledger(), evidenceIndex: evidenceIndex() });
    assert.equal(finals.length, 1);
    assert.equal(finals[0].record.title, "Bootstrap context once");
    assert.ok(finals[0].stagedArtifact.includes(finals[0].record.id));
    assert.equal(finals[0].annotation.verdict, "keep");
  });

  it("annotation owns durable fields: keep without a complete record fails closed", async () => {
    const annotate = await loadAnnotate();
    const stateDir = tmpDir();
    const out = await annotate.annotateStaging([changePlan()], {
      stateDir,
      ledger: ledger(),
      evidenceIndex: evidenceIndex(),
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "ok", annotations: [{ id: "e1", verdict: "keep", reason: "no record supplied" }] };
      },
    });
    assert.deepEqual(out.edits || [], []);
    assert.ok(out.failed);
  });

  it("all measurements need annotation or explicit revert; measurements carry provisional context only", async () => {
    const measure = await loadMeasure();
    assert.equal(typeof measure.measureStaging, "function");
    const stateDir = tmpDir();
    const measurements = measure.measureStaging([changePlan()], { stateDir, ledger: ledger(), evidenceIndex: evidenceIndex() });
    assert.ok(Array.isArray(measurements) && measurements.length === 1);
    for (const m of measurements) {
      assert.ok(m.annotation || m.reverted === true, "measurement needs annotation or explicit revert");
      assert.ok(m.candidateId === "e1");
      assert.ok(m.clusterId === "g-aaa");
      assert.ok(Array.isArray(m.eligibleSources) && m.eligibleSources.length >= 2);
      assert.equal(m.recordId, null, "measurements never carry a final record");
    }
  });

  it("invalid/fake quote/session fails on annotation finals", async () => {
    const annotate = await loadAnnotate();
    const stateDir = tmpDir();
    const badQuote = finalRecord({ evidence: [{ polarity: "negative", text: "made up quote", source: "s1", effect: "m" }] });
    const outQuote = await annotate.annotateStaging([changePlan()], {
      stateDir: tmpDir(),
      ledger: ledger(),
      evidenceIndex: evidenceIndex(),
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "ok", annotations: [{ id: "e1", verdict: "keep", reason: "m", record: badQuote }] };
      },
    });
    assert.ok(outQuote.failed, "fake quote must fail closed");
    assert.deepEqual(outQuote.edits || [], []);
    const badSession = finalRecord({
      sources: ["ghost", "s1"],
      evidence: [
        { polarity: "negative", text: "sessions re-derive project context from scratch", source: "ghost", effect: "m" },
        { polarity: "negative", text: "sessions re-derive project context from scratch", source: "s1", effect: "m" },
      ],
    });
    const outSession = await annotate.annotateStaging([changePlan()], {
      stateDir: tmpDir(),
      ledger: ledger(),
      evidenceIndex: evidenceIndex(),
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "ok", annotations: [{ id: "e1", verdict: "keep", reason: "m", record: badSession }] };
      },
    });
    assert.ok(outSession.failed, "unknown session must fail closed");
    void stateDir;
    void annotate;
  });

  it("annotation failure clears/marks staging and no edits", async () => {
    const annotate = await loadAnnotate();
    const stage = await loadStage();
    const stateDir = tmpDir();
    const staged = stage.stageCandidates([changePlan()], { stateDir, runId: "run-STAGE2" });
    const out = await annotate.annotateStaging(staged, {
      stateDir,
      ledger: ledger(),
      evidenceIndex: evidenceIndex(),
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "failed", error: "boom-annotate" };
      },
    });
    assert.deepEqual(out.edits || [], []);
    assert.ok(out.failed);
    const marker = path.join(stateDir, "staging", "annotate.failed");
    const cleared = !fs.existsSync(path.join(stateDir, "staging", "candidates.json")) || fs.existsSync(marker);
    assert.ok(cleared, "staging must be cleared or marked on annotation failure");
  });

  it("production annotate without final records fails closed (invents nothing)", async () => {
    const annotate = await loadAnnotate();
    const out = await annotate.annotateStaging([changePlan()], {
      stateDir: tmpDir(),
      ledger: ledger(),
      evidenceIndex: evidenceIndex(),
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "ok", annotations: [{ id: "e1", verdict: "keep" }] };
      },
    });
    assert.ok(out.failed);
    assert.deepEqual(out.edits || [], []);
  });

  it("explicit revert/drop yields no final edits", async () => {
    const annotate = await loadAnnotate();
    const stage = await loadStage();
    for (const verdict of ["revert", "drop"]) {
      const out = await annotate.annotateStaging([changePlan()], {
        stateDir: tmpDir(),
        ledger: ledger(),
        evidenceIndex: evidenceIndex(),
        invoke: (args) => {
          if (args.stage === "annotate-preface") return { status: "ok", ready: true };
          return { status: "ok", annotations: [{ id: "e1", verdict, reason: "not supported" }] };
        },
      });
      assert.equal(out.failed, false);
      const finals = stage.buildFinalProposal(out.annotated, { ledger: ledger(), evidenceIndex: evidenceIndex() });
      assert.deepEqual(finals, [], `verdict ${verdict} must yield no finals`);
    }
  });

  it("mock invokes same plan->measure->preface->annotate-final sequence", async () => {
    const pipeline = await import("../src/pipeline.js");
    assert.equal(typeof pipeline.runPipeline, "function");
    const seen = [];
    const trackingInvoke = (stageName) => (args) => {
      seen.push(args?.stage ?? stageName);
      if (stageName === "synthesize") return { status: "ok", plans: [changePlan()] };
      if (stageName === "annotate-preface") return { status: "ok", ready: true };
      if (stageName === "annotate") {
        return { status: "ok", annotations: [annotationKeep()] };
      }
      return { status: "ok", result: {} };
    };
    await pipeline.runPipeline({
      home: tmpDir(),
      stateDir: tmpDir(),
      analyzer: "acpx",
      runId: "run-SEQ1",
      analyzeInvoke: trackingInvoke("analyze"),
      consolidateInvoke: trackingInvoke("consolidate"),
      synthesizeInvoke: trackingInvoke("synthesize"),
      annotateInvoke: trackingInvoke("annotate"),
    });
    const order = seen.filter((s) => ["synthesize", "annotate-preface", "annotate"].includes(s));
    assert.deepEqual(order, ["synthesize", "annotate-preface", "annotate"]);
  });

  it("rendered synthesis/preface/annotate and measurement only in private state", async () => {
    const pipeline = await import("../src/pipeline.js");
    const stateDir = tmpDir();
    const home = tmpDir();
    const dir = path.join(home, ".codex", "sessions");
    fs.mkdirSync(dir, { recursive: true });
    for (let i = 0; i < 2; i += 1) {
      fs.writeFileSync(path.join(dir, `2026-01-0${i + 1}T00-00-00Z.jsonl`), `${JSON.stringify({ role: "user", text: `bootstrap context please ${i}` })}\n`, "utf8");
    }
    await pipeline.runPipeline({
      home,
      stateDir,
      analyzer: "acpx",
      runId: "run-PRIV1",
      analyzeInvoke: () => ({ status: "ok", evidence: { status: "ok", positive: [], negative: [], gaps: [] } }),
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
      synthesizeInvoke: () => ({ status: "ok", result: { plans: [] } }),
    });
    const promptsDir = path.join(stateDir, "prompts");
    assert.ok(fs.existsSync(promptsDir));
    const names = fs.existsSync(promptsDir) ? fs.readdirSync(promptsDir) : [];
    assert.ok(names.some((n) => /synthesis/.test(n)));
    assert.ok(names.some((n) => /preface|annotate/.test(n)));
    assert.ok(names.some((n) => /measure/.test(n)));
    const leaked = names.filter((n) => /synthesis|preface|annotate|measure/.test(n) && !n.startsWith("run-"));
    assert.deepEqual(leaked, []);
    if (process.platform !== "win32") {
      for (const n of names.filter((f) => /preface|annotate|measure/.test(f))) {
        assert.equal(fs.statSync(path.join(promptsDir, n)).mode & 0o777, 0o600);
      }
    }
    assert.ok(!fs.existsSync(path.join(SRC, "prompts-rendered.md")));
  });

  it("rejection suppression applies to annotated final records only", async () => {
    const annotate = await loadAnnotate();
    assert.equal(typeof annotate.applyRejectionSuppression, "function");
    const rejections = [{ edit: "e1", title: "Bootstrap context once", clusterId: "g-aaa", sources: ["s1", "s2"] }];
    const annotated = [{ ...changePlan(), annotation: { verdict: "keep", reason: "m", record: finalRecord() }, finalRecord: finalRecord() }];
    const out = annotate.applyRejectionSuppression(annotated, rejections, { evidenceIndex: evidenceIndex() });
    assert.equal(out.length, 0);
    const higherRecord = { ...finalRecord(), sources: ["s1", "s2", "s3"], evidence: [...finalRecord().evidence, { polarity: "negative", text: "sessions re-derive project context from scratch", source: "s3", effect: "m" }] };
    const higher = { ...changePlan(), annotation: { verdict: "keep", reason: "m", record: higherRecord }, finalRecord: higherRecord };
    const idx = new Map([
      ...evidenceIndex(),
      ["s3", [{ quote: "sessions re-derive project context from scratch", effect: "e3" }]],
    ]);
    const kept = annotate.applyRejectionSuppression([higher], rejections, { evidenceIndex: idx });
    assert.equal(kept.length, 1);
  });

  it("rejection suppression never erases explicit drop/revert annotations", async () => {
    const annotate = await loadAnnotate();
    const rejections = [{ edit: "e1", title: "Bootstrap context once", clusterId: "g-aaa", sources: ["s1", "s2"] }];
    // Same rejected identity, but explicit drop/revert carry no final record.
    const dropped = { ...changePlan({ id: "e1" }), annotation: { verdict: "drop", reason: "not supported" } };
    const reverted = { ...changePlan({ id: "e2" }), annotation: { verdict: "revert", reason: "operator reverted" } };
    const survived = annotate.applyRejectionSuppression([dropped, reverted], rejections, { evidenceIndex: evidenceIndex() });
    assert.equal(survived.length, 2, "drop/revert annotations must survive rejection suppression");
    assert.deepEqual(survived.map((c) => c?.annotation?.verdict).sort(), ["drop", "revert"]);
    // Control: equivalent keep final record with the same identity IS suppressible.
    const keep = { ...changePlan({ id: "e3" }), annotation: { verdict: "keep", reason: "m", record: finalRecord() }, finalRecord: finalRecord() };
    const suppressed = annotate.applyRejectionSuppression([keep], rejections, { evidenceIndex: evidenceIndex() });
    assert.equal(suppressed.length, 0, "equivalent keep final must stay suppressible");
  });
});

describe("review findings: per-change measured binding (no blanket all-IDs)", () => {
  function twoPlans() {
    return [
      { id: "e1", kind: "add", clusterId: "g-aaa", provisionalIntent: "Bootstrap context once", provisionalSources: ["s1", "s2"], provisionalCount: 2 },
      { id: "e2", kind: "add", clusterId: "g-aaa", provisionalIntent: "Bootstrap context once", provisionalSources: ["s1", "s2"], provisionalCount: 2 },
    ];
  }
  function workspaceChanges() {
    return [
      { id: "m-e1", recordId: "e1", file: "e1.md", kind: "created", text: "sessions re-derive project context from scratch", diff: "--- a (m-e1)\n+++ b/e1.md (m-e1)\n+sessions re-derive project context from scratch", clusterId: "g-aaa", provisionalSources: ["s1", "s2"], eligibleSources: ["s1", "s2"], sources: ["s1", "s2"] },
      { id: "m-e2", recordId: "e2", file: "e2.md", kind: "created", text: "sessions re-derive project context from scratch", diff: "--- a (m-e2)\n+++ b/e2.md (m-e2)\n+sessions re-derive project context from scratch", clusterId: "g-aaa", provisionalSources: ["s1", "s2"], eligibleSources: ["s1", "s2"], sources: ["s1", "s2"] },
      { id: "m-other", recordId: "other", file: "other.md", kind: "modified", before: "x", text: "y", diff: "--- a (m-other)\n+++ b (m-other)" },
    ];
  }
  it("annotateStaging binds each keep to its specific change only", async () => {
    const annotate = await loadAnnotate();
    const out = await annotate.annotateStaging(twoPlans(), {
      stateDir: tmpDir(),
      ledger: ledger(),
      evidenceIndex: evidenceIndex(),
      measuredChanges: workspaceChanges(),
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "ok", annotations: [
          { id: "e1", verdict: "keep", reason: "m", record: finalRecord() },
          { id: "e2", verdict: "keep", reason: "m", record: { ...finalRecord(), id: "exp-second-a1b2c3d4e5f6" } },
        ]};
      },
    });
    assert.equal(out.failed, false);
    assert.equal(out.annotated.length, 2);
    const e1 = out.annotated.find((a) => a.id === "e1");
    const e2 = out.annotated.find((a) => a.id === "e2");
    assert.deepEqual(e1.measuredIds, ["m-e1"]);
    assert.deepEqual(e2.measuredIds, ["m-e2"]);
  });
  it("buildFinalProposal binds each final to its specific change only", async () => {
    const stage = await loadStage();
    const annotate = await loadAnnotate();
    const out = await annotate.annotateStaging(twoPlans(), {
      stateDir: tmpDir(),
      ledger: ledger(),
      evidenceIndex: evidenceIndex(),
      measuredChanges: workspaceChanges(),
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "ok", annotations: [
          { id: "e1", verdict: "keep", reason: "m", record: finalRecord() },
          { id: "e2", verdict: "keep", reason: "m", record: { ...finalRecord(), id: "exp-second-a1b2c3d4e5f6" } },
        ]};
      },
    });
    const finals = stage.buildFinalProposal(out.annotated, {
      stateDir: null,
      ledger: ledger(),
      evidenceIndex: evidenceIndex(),
      measuredChanges: workspaceChanges(),
    });
    assert.equal(finals.length, 2);
    const f1 = finals.find((f) => f.id === "e1");
    const f2 = finals.find((f) => f.id === "e2");
    assert.deepEqual(f1.measuredIds, ["m-e1"]);
    assert.deepEqual(f2.measuredIds, ["m-e2"]);
    assert.ok(!f1.measuredIds.includes("m-e2") && !f1.measuredIds.includes("m-other"));
    assert.ok(!JSON.stringify(workspaceChanges()).includes("seed-"), "synthetic seed records do not exist");
  });
});

describe("annotate prompt binds staged session-bound allowed evidence", () => {
  function distinctLedger() {
    return {
      version: 1,
      minGapEvidence: 2,
      clusters: [
        {
          id: "g-bbb",
          proposedInstruction: "Rebuild index incrementally",
          representativeQuote: "representative fallback quote",
          mistake: "rebuilds full index every run",
          sources: ["s1", "s2"],
          count: 2,
          eligible: true,
          perSource: {
            s1: { quote: "alpha exact quote from session one", mistake: "m" },
            s2: { quote: "beta exact quote from session two", mistake: "m" },
          },
        },
      ],
    };
  }
  function distinctIndex() {
    return new Map([
      ["s1", [{ quote: "alpha exact quote from session one", effect: "e1" }]],
      ["s2", [{ quote: "beta exact quote from session two", effect: "e2" }]],
      ["s3-global", [{ quote: "unrelated global quote must not leak", effect: "eg" }]],
    ]);
  }
  function distinctPlan(overrides = {}) {
    return {
      id: "e9",
      kind: "add",
      clusterId: "g-bbb",
      provisionalIntent: "Rebuild index incrementally",
      provisionalSources: ["s1", "s2"],
      provisionalCount: 2,
      ...overrides,
    };
  }
  function distinctRecord(overrides = {}) {
    return {
      id: "exp-rebuild-b1c2d3e4f5a6",
      title: "Rebuild index incrementally",
      body: "Recurring gap seen in 2 session(s): rebuilds full index every run",
      sources: ["s1", "s2"],
      clusterId: "g-bbb",
      evidence: [
        { polarity: "negative", text: "alpha exact quote from session one", source: "s1", effect: "m" },
        { polarity: "negative", text: "beta exact quote from session two", source: "s2", effect: "m" },
      ],
      counterevidence: "none observed",
      compilerImplication: "compiler appends this record to the experience block",
      ...overrides,
    };
  }

  it("prompt lists exact source-specific allowed quotes (bounded, no global leak)", async () => {
    const annotate = await loadAnnotate();
    const prompt = annotate.renderAnnotatePrompt([distinctPlan()], {
      runId: "run-ALLOW1",
      ledger: distinctLedger(),
      evidenceIndex: distinctIndex(),
    });
    assert.ok(prompt.includes("alpha exact quote from session one"), "prompt must list s1 exact quote");
    assert.ok(prompt.includes("beta exact quote from session two"), "prompt must list s2 exact quote");
    assert.ok(prompt.includes("[s1]"), "prompt must bind s1 source id");
    assert.ok(prompt.includes("[s2]"), "prompt must bind s2 source id");
    assert.ok(!prompt.includes("unrelated global quote must not leak"), "prompt must not show arbitrary global evidence");
  });

  it("swapped or paraphrased quote still fails closed", async () => {
    const annotate = await loadAnnotate();
    const swapped = distinctRecord({
      evidence: [
        { polarity: "negative", text: "beta exact quote from session two", source: "s1", effect: "m" },
        { polarity: "negative", text: "alpha exact quote from session one", source: "s2", effect: "m" },
      ],
    });
    const outSwapped = await annotate.annotateStaging([distinctPlan()], {
      stateDir: tmpDir(),
      ledger: distinctLedger(),
      evidenceIndex: distinctIndex(),
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "ok", annotations: [{ id: "e9", verdict: "keep", reason: "m", record: swapped }] };
      },
    });
    assert.ok(outSwapped.failed, "swapped cross-source quote must fail closed");
    assert.deepEqual(outSwapped.edits || [], []);
    const paraphrased = distinctRecord({
      evidence: [
        { polarity: "negative", text: "alpha exact quote from session one (reworded)", source: "s1", effect: "m" },
        { polarity: "negative", text: "beta exact quote from session two", source: "s2", effect: "m" },
      ],
    });
    const outPara = await annotate.annotateStaging([distinctPlan()], {
      stateDir: tmpDir(),
      ledger: distinctLedger(),
      evidenceIndex: distinctIndex(),
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "ok", annotations: [{ id: "e9", verdict: "keep", reason: "m", record: paraphrased }] };
      },
    });
    assert.ok(outPara.failed, "paraphrased/reconstructed quote must fail closed");
    assert.deepEqual(outPara.edits || [], []);
  });

  it("live-shaped fixture with exact copied evidence succeeds", async () => {
    const annotate = await loadAnnotate();
    const out = await annotate.annotateStaging([distinctPlan()], {
      stateDir: tmpDir(),
      ledger: distinctLedger(),
      evidenceIndex: distinctIndex(),
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "ok", annotations: [{ id: "e9", verdict: "keep", reason: "m", record: distinctRecord() }] };
      },
    });
    assert.equal(out.failed, false);
    assert.equal(out.annotated.length, 1);
    assert.equal(out.annotated[0].finalRecord.evidence[0].text, "alpha exact quote from session one");
    assert.equal(out.annotated[0].finalRecord.evidence[1].text, "beta exact quote from session two");
  });

  it("long quotes are never sliced: complete or omitted as a whole", async () => {
    const annotate = await loadAnnotate();
    const longQuote = `LONG-START-${"x".repeat(600)}-LONG-END`;
    assert.ok(longQuote.length > 500, "fixture must exceed the old 500-char cap");
    const longLedger = {
      version: 1,
      minGapEvidence: 2,
      clusters: [
        {
          id: "g-bbb",
          proposedInstruction: "Rebuild index incrementally",
          representativeQuote: "representative fallback quote",
          mistake: "rebuilds full index every run",
          sources: ["s1", "s2"],
          count: 2,
          eligible: true,
          perSource: {
            s1: { quote: longQuote, mistake: "m" },
            s2: { quote: "beta exact quote from session two", mistake: "m" },
          },
        },
      ],
    };
    const longIndex = new Map([
      ["s1", [{ quote: longQuote, effect: "e1" }]],
      ["s2", [{ quote: "beta exact quote from session two", effect: "e2" }]],
    ]);
    const prompt = annotate.renderAnnotatePrompt([distinctPlan()], {
      runId: "run-LONG1",
      ledger: longLedger,
      evidenceIndex: longIndex,
    });
    const prefix = longQuote.slice(0, 500);
    // Either the complete quote renders, or the whole quote is skipped:
    // a 500-char prefix must never appear without the full text + END marker.
    assert.ok(!prompt.includes(prefix) || prompt.includes(longQuote), "long quote must not appear as a truncated prefix");
    if (prompt.includes("LONG-START-")) {
      assert.ok(prompt.includes(longQuote), "started long quote must render complete");
      assert.ok(prompt.includes("-LONG-END"), "complete long quote must keep its END marker");
    }
    // Over-budget quotes are skipped as a whole: a quote larger than the
    // total budget leaves no fragment behind.
    const hugeQuote = `HUGE-START-${"y".repeat(20000)}-HUGE-END`;
    const hugeLedger = {
      version: 1,
      minGapEvidence: 2,
      clusters: [
        {
          id: "g-bbb",
          proposedInstruction: "Rebuild index incrementally",
          representativeQuote: "representative fallback quote",
          mistake: "rebuilds full index every run",
          sources: ["s1"],
          count: 1,
          eligible: true,
          perSource: { s1: { quote: hugeQuote, mistake: "m" } },
        },
      ],
    };
    const hugeIndex = new Map([["s1", [{ quote: hugeQuote, effect: "e1" }]]]);
    const hugePrompt = annotate.renderAnnotatePrompt([distinctPlan({ provisionalSources: ["s1"] })], {
      runId: "run-HUGE1",
      ledger: hugeLedger,
      evidenceIndex: hugeIndex,
    });
    assert.ok(!hugePrompt.includes("HUGE-START-") || hugePrompt.includes(hugeQuote), "over-budget quote must be whole or omitted");
    assert.ok(!hugePrompt.includes(hugeQuote.slice(0, 500)) || hugePrompt.includes("-HUGE-END"), "over-budget quote must never leak a truncated prefix");
  });
});
