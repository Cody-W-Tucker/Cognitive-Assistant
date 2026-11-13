import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { annotate, isValidRecordId, renderAnnotatePrompt, validateRecord } from "../src/annotate.js";
import { QUOTE_A, QUOTE_B, evidenceIndex, ledger, plan, record, tmpDir } from "./helpers.mjs";

const errorsFor = (overrides) => validateRecord(record(overrides), { ledger: ledger(), evidenceIndex: evidenceIndex() });
const soul = { text: "SOUL TEXT", sha256: "abc123" };

describe("record ids", () => {
  it("must be exp-<slug>-<12-char hash>", () => {
    assert.equal(isValidRecordId("exp-bootstrap-context-a1b2c3d4e5f6"), true);
    for (const bad of [undefined, "", "e1", "exp-x", "exp-x-abc", "exp-x-a1b2c3d4e5f6a", "exp-../x-a1b2c3d4e5f6", "exp-x_y-a1b2c3d4e5f6", "/tmp/exp-x-a1b2c3d4e5f6"]) {
      assert.equal(isValidRecordId(bad), false, String(bad));
    }
  });
});

describe("record validation", () => {
  it("accepts a complete record whose quotes belong to their cited sources", () => {
    assert.deepEqual(errorsFor({}), []);
  });

  it("requires id, title, bounded body, counterevidence, and compiler implication", () => {
    for (const [field, value, pattern] of [
      ["id", undefined, /record\.id/],
      ["id", "e1", /record\.id/],
      ["title", " ", /title/],
      ["body", "", /body/],
      ["body", "x".repeat(2001), /exceeds 2000/],
      ["counterevidence", "", /counterevidence/],
      ["compilerImplication", undefined, /compilerImplication/],
    ]) {
      assert.match(errorsFor({ [field]: value }).join("; "), pattern, `${field}=${value}`);
    }
  });

  it("requires an eligible known cluster with >=2 distinct sources from it", () => {
    assert.match(errorsFor({ clusterId: "g-nope" }).join(), /unknown cluster/);
    assert.match(errorsFor({ clusterId: "g-inelig" }).join(), /not eligible/);
    assert.match(errorsFor({ sources: ["s1", "s1"] }).join(), /needs >=2 distinct/);
    const outsider = errorsFor({
      sources: ["s1", "s9"],
      evidence: [
        { text: QUOTE_A, source: "s1" },
        { text: "outsider quote nine", source: "s9" },
      ],
    });
    assert.match(outsider.join(), /not evidence from cluster g-aaa/);
  });

  it("binds each quote to its own source: paraphrased or swapped quotes fail", () => {
    assert.match(errorsFor({ evidence: [{ text: `${QUOTE_A}!`, source: "s1" }, { text: QUOTE_B, source: "s2" }] }).join(), /not an exact quote from source s1/);
    assert.match(errorsFor({ evidence: [{ text: QUOTE_B, source: "s1" }, { text: QUOTE_A, source: "s2" }] }).join(), /not an exact quote/);
  });

  it("requires record.sources to equal the evidence source set", () => {
    assert.match(errorsFor({ evidence: [{ text: QUOTE_A, source: "s1" }] }).join(), /exactly match|needs >=2/);
  });
});

describe("annotate", () => {
  const run = (reply, plans = [plan()]) =>
    annotate(plans, { invoke: async () => reply, stateDir: tmpDir(), runId: "run-1", ledger: ledger(), evidenceIndex: evidenceIndex(), soul });

  it("keeps a valid record and passes drop/revert verdicts through without edits", async () => {
    const out = await run({ annotations: [{ id: "e1", verdict: "keep", reason: "recurs", record: record() }] });
    assert.equal(out.failed, false);
    assert.deepEqual(out.kept[0].annotation, { verdict: "keep", reason: "recurs" });
    assert.deepEqual(out.kept[0].record, record());
    for (const verdict of ["drop", "revert"]) {
      const skip = await run({ annotations: [{ id: "e1", verdict, reason: "no" }] });
      assert.deepEqual([skip.failed, skip.kept, skip.annotated], [false, [], 1]);
    }
  });

  it("fails the whole annotation on a missing verdict, an unknown verdict, or an invalid kept record", async () => {
    const plans = [plan(), plan({ id: "e2" })];
    for (const reply of [
      { annotations: [{ id: "e1", verdict: "keep", record: record() }] },
      { annotations: [{ id: "e1", verdict: "maybe" }, { id: "e2", verdict: "drop" }] },
      { annotations: [{ id: "e1", verdict: "keep", record: record({ id: "e1" }) }, { id: "e2", verdict: "drop" }] },
      { annotations: [{ id: "e1", verdict: "keep" }, { id: "e2", verdict: "drop" }] },
      { verdicts: [] },
    ]) {
      const out = await run(reply, plans);
      assert.equal(out.failed, true, JSON.stringify(reply));
      assert.deepEqual(out.kept, []);
      assert.match(out.note, /annotate failed/);
    }
  });

  it("rejects a dropped plan's cluster and sources outside the kept plan", async () => {
    const led = ledger();
    led.clusters[0].sources.push("s9");
    led.clusters.push({ ...led.clusters[0], id: "g-bbb" });
    const plans = [plan(), plan({ id: "e2", clusterId: "g-bbb" })];
    const foreignSources = record({
      sources: ["s1", "s9"],
      evidence: [{ source: "s1", text: QUOTE_A }, { source: "s9", text: "outsider quote nine" }],
    });
    for (const candidate of [record({ clusterId: "g-bbb" }), foreignSources]) {
      assert.deepEqual(validateRecord(candidate, { ledger: led, evidenceIndex: evidenceIndex() }), []);
      const out = await annotate(plans, {
        invoke: async () => ({ annotations: [
          { id: "e1", verdict: "keep", record: candidate },
          { id: "e2", verdict: "drop" },
        ] }),
        stateDir: tmpDir(), runId: "run-1", ledger: led, evidenceIndex: evidenceIndex(), soul,
      });
      assert.equal(out.failed, true);
      assert.deepEqual(out.kept, []);
      assert.match(out.note, /must match the plan cluster|not in plan.provisionalSources/);
    }
  });

  it("the prompt lists each plan's exact allowed quotes and never slices one", () => {
    const long = `${"long quote ".repeat(900)}end`;
    const led = ledger();
    led.clusters[0].perSource.s2.quote = long;
    const index = new Map([["s1", [{ quote: QUOTE_A }]]]);
    const prompt = renderAnnotatePrompt([plan()], { runId: "run-1", ledger: led, evidenceIndex: index, soul });
    assert.ok(prompt.includes(`- [s1] ${JSON.stringify(QUOTE_A)}`));
    assert.ok(prompt.includes("- [s2] (no staged quote)"), "a quote over the budget is omitted whole");
    assert.ok(!prompt.includes("long quote long"));
    assert.ok(prompt.includes("SOUL TEXT") && prompt.includes("abc123"));
  });
});
