import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  validateProvisionalPlans,
  materializeValidatedPlans,
  parseStrictBoundedSynthesisStdout,
  parseAcpxSynthesisResult,
} from "../src/synthesize.js";

function ledger() {
  return {
    minGapEvidence: 2,
    clusters: [
      { id: "g-aaa", eligible: true, sources: ["s1", "s2"], count: 2, proposedInstruction: "Do X" },
    ],
  };
}

function validPlan(over = {}) {
  return {
    id: "e1",
    kind: "add",
    clusterId: "g-aaa",
    provisionalIntent: "Do X",
    provisionalSources: ["s1", "s2"],
    provisionalCount: 2,
    ...over,
  };
}

describe("strict audit: bounded synthesis stdout is exactly one JSON object", () => {
  it("accepts exact {plans:[...]} stdout", () => {
    const parsed = parseStrictBoundedSynthesisStdout(`{"plans": []}`);
    assert.deepEqual(parsed, { plans: [] });
  });

  it("rejects prose-embedded JSON", () => {
    assert.equal(parseStrictBoundedSynthesisStdout(`Here is your result: {"plans": []} hope this helps`), null);
  });

  it("rejects fenced wrapping", () => {
    assert.equal(parseStrictBoundedSynthesisStdout("```json\n{\"plans\": []}\n```"), null);
  });

  it("rejects array-wrapped payload", () => {
    assert.equal(parseStrictBoundedSynthesisStdout(`[{"plans": []}]`), null);
  });

  it("rejects trailing prose after JSON", () => {
    assert.equal(
      parseStrictBoundedSynthesisStdout(`{"plans": []}\nLet me explain...`),
      null,
    );
  });
});

describe("strict audit: root payload is exactly {plans:[...]}", () => {
  it("rejects extra top-level fields", () => {
    for (const raw of [
      { plans: [], title: "x" },
      { plans: [], status: "ok" },
      { plans: [], body: "a { b } c" },
    ]) {
      const check = validateProvisionalPlans(raw, { ledger: ledger(), floor: 2 });
      assert.equal(check.ok, false, `should reject ${JSON.stringify(raw)}`);
      assert.equal(parseAcpxSynthesisResult(raw), null);
      assert.equal(parseStrictBoundedSynthesisStdout(JSON.stringify(raw)), null);
    }
  });

  it("accepts exact {plans:[...]} root", () => {
    const check = validateProvisionalPlans({ plans: [validPlan()] }, { ledger: ledger(), floor: 2 });
    assert.equal(check.ok, true);
    assert.deepEqual(parseAcpxSynthesisResult({ plans: [validPlan()] }), [validPlan()]);
  });
});

describe("strict audit: materializeValidatedPlans fails closed on unvalidated plans", () => {
  function tmpState() {
    return fs.mkdtempSync(path.join(os.tmpdir(), "synth-audit-"));
  }

  it("rejects authoritative final fields", () => {
    const dir = tmpState();
    assert.throws(
      () => materializeValidatedPlans([validPlan({ record: { title: "x" } })], { stateDir: dir }),
      /authoritative|unvalidated|refuse/,
    );
    assert.throws(
      () => materializeValidatedPlans([validPlan({ title: "x" })], { stateDir: dir }),
      /authoritative|unvalidated|refuse/,
    );
  });

  it("rejects missing intent/sources", () => {
    const dir = tmpState();
    assert.throws(
      () => materializeValidatedPlans([{ id: "e1", kind: "add", clusterId: "g-aaa", provisionalSources: ["s1", "s2"] }], { stateDir: dir }),
      /provisionalIntent|unvalidated|refuse/,
    );
    assert.throws(
      () => materializeValidatedPlans([{ id: "e1", kind: "add", clusterId: "g-aaa", provisionalIntent: "x", provisionalSources: ["only-one"] }], { stateDir: dir }),
      /provisionalSources|unvalidated|refuse/,
    );
  });

  it("rejects model-controlled path target", () => {
    const dir = tmpState();
    assert.throws(
      () => materializeValidatedPlans([{ ...validPlan(), file: "../../evil.md" }], { stateDir: dir }),
      /filesystem|refuse|unvalidated/,
    );
  });

  it("accepts validated narrow plans", () => {
    const dir = tmpState();
    const { written } = materializeValidatedPlans([validPlan()], { stateDir: dir });
    assert.deepEqual(written, ["e1.md"]);
  });
});
