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

function stagedCandidate(overrides = {}) {
  return {
    id: "e1",
    kind: "add",
    title: "Bootstrap context once",
    record: {
      id: "exp-x",
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
    evidence: [
      { polarity: "negative", text: "sessions re-derive project context from scratch", source: "s1", effect: "m" },
      { polarity: "negative", text: "sessions re-derive project context from scratch", source: "s2", effect: "m" },
    ],
    stagedArtifact: "artifact",
    diff: "diff",
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

describe("synth->private stage / measure->annotate-preface->annotate (RED)", () => {
  it("preface precedes annotate with sentinel first", async () => {
    const annotate = await loadAnnotate();
    assert.equal(typeof annotate.renderAnnotatePreface, "function");
    assert.equal(typeof annotate.annotateStaging, "function");
    const calls = [];
    const stateDir = tmpDir();
    const preface = annotate.renderAnnotatePreface(stagedCandidate(), { stateDir });
    assert.ok(String(preface).startsWith("<!-- ca-improve:self-session -->\n"));
    await annotate.annotateStaging([stagedCandidate()], {
      stateDir,
      invoke: (args) => {
        calls.push(args.stage);
        return { status: "ok", annotations: [{ id: "e1", verdict: "keep" }] };
      },
    });
    assert.deepEqual(calls, ["annotate-preface", "annotate"]);
  });

  it("unannotated staged candidates cannot reach apply/final proposal", async () => {
    const stage = await loadStage();
    assert.equal(typeof stage.stageCandidates, "function");
    assert.equal(typeof stage.buildFinalProposal, "function");
    const stateDir = tmpDir();
    const staged = stage.stageCandidates([stagedCandidate()], { stateDir, runId: "run-STAGE1" });
    assert.ok(staged && staged.length === 1);
    assert.throws(() => stage.buildFinalProposal(staged, { stateDir }), /annotat/i);
  });

  it("all measurements need annotation or explicit revert", async () => {
    const measure = await loadMeasure();
    assert.equal(typeof measure.measureStaging, "function");
    const stateDir = tmpDir();
    const measurements = measure.measureStaging([stagedCandidate()], { stateDir });
    assert.ok(Array.isArray(measurements) && measurements.length === 1);
    for (const m of measurements) {
      assert.ok(m.annotation || m.reverted === true, "measurement needs annotation or explicit revert");
    }
  });

  it("invalid/fake quote/session fails", async () => {
    const stage = await loadStage();
    assert.equal(typeof stage.validateStaged, "function");
    const badQuote = stagedCandidate({
      evidence: [{ polarity: "negative", text: "made up quote", source: "s1" }],
    });
    assert.equal(stage.validateStaged(badQuote, { ledger: ledger(), evidenceIndex: evidenceIndex() }).ok, false);
    const badSession = stagedCandidate({
      evidence: [
        { polarity: "negative", text: "sessions re-derive project context from scratch", source: "ghost" },
      ],
    });
    assert.equal(stage.validateStaged(badSession, { ledger: ledger(), evidenceIndex: evidenceIndex() }).ok, false);
  });

  it("annotation failure clears/marks staging and no edits", async () => {
    const annotate = await loadAnnotate();
    const stage = await loadStage();
    const stateDir = tmpDir();
    const staged = (await import("../src/stage.js")).stageCandidates
      ? stage.stageCandidates([stagedCandidate()], { stateDir, runId: "run-STAGE2" })
      : [stagedCandidate()];
    const out = await annotate.annotateStaging(staged, {
      stateDir,
      invoke: () => ({ status: "failed", error: "boom-annotate" }),
    });
    assert.deepEqual(out.edits || [], []);
    assert.ok(out.failed);
    const marker = path.join(stateDir, "staging", "annotate.failed");
    const cleared = !fs.existsSync(path.join(stateDir, "staging", "candidates.json")) || fs.existsSync(marker);
    assert.ok(cleared, "staging must be cleared or marked on annotation failure");
  });

  it("mock invokes same sequence", async () => {
    const pipeline = await import("../src/pipeline.js");
    assert.equal(typeof pipeline.runPipeline, "function");
    const seen = [];
    const trackingInvoke = (stageName) => (args) => {
      seen.push(args?.stage ?? stageName);
      if (stageName === "synthesize") return { status: "ok", candidates: [stagedCandidate()] };
      if (stageName === "annotate-preface" || stageName === "annotate") {
        return { status: "ok", annotations: [{ id: "e1", verdict: "keep" }] };
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
      synthesizeInvoke: () => ({ status: "ok", result: { candidates: [] } }),
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

  it("rejection suppression applies final annotations", async () => {
    const annotate = await loadAnnotate();
    assert.equal(typeof annotate.applyRejectionSuppression, "function");
    const rejections = [{ edit: "e1", title: "Bootstrap context once", clusterId: "g-aaa", sources: ["s1", "s2"] }];
    const annotated = [{ ...stagedCandidate(), annotation: { verdict: "keep" } }];
    const out = annotate.applyRejectionSuppression(annotated, rejections, { evidenceIndex: evidenceIndex() });
    assert.equal(out.length, 0);
    const higher = {
      ...stagedCandidate(),
      annotation: { verdict: "keep" },
      record: { ...stagedCandidate().record, sources: ["s1", "s2", "s3"] },
    };
    const idx = new Map([
      ...evidenceIndex(),
      ["s3", [{ quote: "sessions re-derive project context from scratch", effect: "e3" }]],
    ]);
    const kept = annotate.applyRejectionSuppression([higher], rejections, { evidenceIndex: idx });
    assert.equal(kept.length, 1);
  });
});
