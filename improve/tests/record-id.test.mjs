import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "ca-record-id-"));
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

// Deterministic, candidate-bound experience-record id in the mock shape:
// exp-<slug(intent)>-<12-hex-hash(clusterId)>.
const VALID_RECORD_ID = "exp-bootstrap-context-once-a1b2c3d4e5f6";

function validRecord(overrides = {}) {
  return {
    id: VALID_RECORD_ID,
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

function keepWith(record) {
  return { id: "e1", verdict: "keep", reason: "m", record };
}

async function loadAnnotate() {
  return import("../src/annotate.js");
}

async function loadStage() {
  return import("../src/stage.js");
}

describe("record.id required for all keep annotations (fail-first)", () => {
  it("annotation rejects a keep whose record has no id", async () => {
    const annotate = await loadAnnotate();
    const { id: _dropped, ...noId } = validRecord();
    void _dropped;
    const out = await annotate.annotateStaging([changePlan()], {
      stateDir: tmpDir(),
      ledger: ledger(),
      evidenceIndex: evidenceIndex(),
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "ok", annotations: [keepWith(noId)] };
      },
    });
    assert.ok(out.failed, "keep without record.id must fail closed");
    assert.deepEqual(out.edits || [], []);
  });

  it("final proposal rejects a keep whose record has no id", async () => {
    const stage = await loadStage();
    const { id: _dropped, ...noId } = validRecord();
    void _dropped;
    const annotated = [
      { ...changePlan(), annotation: { verdict: "keep", reason: "m", record: noId }, finalRecord: noId },
    ];
    assert.throws(
      () => stage.buildFinalProposal(annotated, { ledger: ledger(), evidenceIndex: evidenceIndex() }),
      /record\.id|record id/i,
    );
  });

  it("validateCandidate rejects a record with no id", async () => {
    const { validateCandidate } = await import("../src/synthesize.js");
    const { id: _dropped, ...noId } = validRecord();
    void _dropped;
    const res = validateCandidate({ record: noId }, { ledger: ledger(), evidenceIndex: evidenceIndex() });
    assert.equal(res.ok, false);
    assert.ok((res.errors || []).some((e) => /record\.id|record id/i.test(String(e))));
  });

  it("run-local plan id is not a valid record id", async () => {
    const annotate = await loadAnnotate();
    const out = await annotate.annotateStaging([changePlan()], {
      stateDir: tmpDir(),
      ledger: ledger(),
      evidenceIndex: evidenceIndex(),
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "ok", annotations: [keepWith(validRecord({ id: "e1" }))] };
      },
    });
    assert.ok(out.failed, "record.id reusing the run-local plan id must fail closed");
    assert.deepEqual(out.edits || [], []);
  });

  it("unsafe record id is rejected", async () => {
    const stage = await loadStage();
    for (const badId of ["../evil", "e1.md", "", "  "]) {
      const rec = validRecord({ id: badId });
      const annotated = [
        { ...changePlan(), annotation: { verdict: "keep", reason: "m", record: rec }, finalRecord: rec },
      ];
      assert.throws(
        () => stage.buildFinalProposal(annotated, { ledger: ledger(), evidenceIndex: evidenceIndex() }),
        /record\.id|record id/i,
        `unsafe record id ${JSON.stringify(badId)} must throw`,
      );
    }
  });

  it("record id without hash suffix is rejected", async () => {
    const { isValidRecordId, validateCandidate } = await import("../src/synthesize.js");
    for (const badId of [
      "exp-bootstrap-context-once",
      "exp-bootstrap",
      "exp-a1b2c3d4e5f6",
    ]) {
      assert.equal(isValidRecordId(badId), false, `no-hash id ${JSON.stringify(badId)} must be invalid`);
      const res = validateCandidate({ record: validRecord({ id: badId }) }, { ledger: ledger(), evidenceIndex: evidenceIndex() });
      assert.equal(res.ok, false, `no-hash id ${JSON.stringify(badId)} must fail validation`);
    }
  });

  it("record id with wrong-length hash suffix is rejected", async () => {
    const { isValidRecordId, validateCandidate } = await import("../src/synthesize.js");
    for (const badId of [
      "exp-bootstrap-context-once-a1b2c3",
      "exp-bootstrap-context-once-a1b2c3d4e5f6a1",
      "exp-bootstrap-context-once-",
      "exp-bootstrap-context-once-a1b2c3d4e5f!",
      "exp--a1b2c3d4e5f6",
    ]) {
      assert.equal(isValidRecordId(badId), false, `wrong-hash id ${JSON.stringify(badId)} must be invalid`);
      const res = validateCandidate({ record: validRecord({ id: badId }) }, { ledger: ledger(), evidenceIndex: evidenceIndex() });
      assert.equal(res.ok, false, `wrong-hash id ${JSON.stringify(badId)} must fail validation`);
    }
  });

  it("live-shaped keep with a valid id stages artifact/diff under that id", async () => {
    const annotate = await loadAnnotate();
    const out = await annotate.annotateStaging([changePlan()], {
      stateDir: tmpDir(),
      ledger: ledger(),
      evidenceIndex: evidenceIndex(),
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "ok", annotations: [keepWith(validRecord())] };
      },
    });
    assert.equal(out.failed, false);
    assert.equal(out.annotated.length, 1);
    const staged = out.annotated[0];
    assert.equal(staged.finalRecord.id, VALID_RECORD_ID);
    assert.ok(String(staged.stagedArtifact).includes(`id: ${VALID_RECORD_ID}`));
    assert.ok(
      String(staged.diff).includes(`+++ staged/${VALID_RECORD_ID}.md`),
      "diff must be bound to the annotation record id, never the run-local plan id",
    );
    assert.ok(
      !String(staged.diff).includes("+++ staged/e1.md"),
      "diff must not fall back to the run-local staged plan id",
    );
  });

  it("mock final builder emits a deterministic candidate-bound record id", async () => {
    const annotate = await loadAnnotate();
    const plan = changePlan();
    const first = annotate.buildMockFinalAnnotation(plan, { ledger: ledger(), evidenceIndex: evidenceIndex() });
    const second = annotate.buildMockFinalAnnotation(plan, { ledger: ledger(), evidenceIndex: evidenceIndex() });
    assert.ok(String(first.record.id).startsWith("exp-"));
    assert.equal(first.record.id, second.record.id, "mock record id must be deterministic");
    assert.notEqual(first.record.id, plan.id, "record id must not reuse the run-local plan id");
  });
});
