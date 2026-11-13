import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import { MAX_PLANS, renderRejections, synthesize, validatePlans } from "../src/synthesize.js";
import { evidenceIndex, ledger, plan, tmpDir } from "./helpers.mjs";

const check = (reply, floor = 2) => validatePlans(reply, { ledger: ledger(), floor });

describe("synthesis plan validation", () => {
  it("accepts {plans:[...]} and normalizes each plan", () => {
    const out = check({ plans: [{ clusterId: "g-aaa", provisionalIntent: " Bootstrap ", provisionalSources: ["s1", "s2", "s1"] }] });
    assert.equal(out.ok, true);
    assert.deepEqual(out.plans, [plan({ provisionalIntent: "Bootstrap" })]);
    assert.deepEqual(check({ plans: [] }), { ok: true, plans: [], errors: [] });
  });

  it("rejects any root other than exactly {plans:[...]}", () => {
    for (const reply of [null, [], { plans: "x" }, { candidates: [] }, { edits: [] }, { plans: [], note: "extra" }]) {
      assert.equal(check(reply).ok, false, JSON.stringify(reply));
    }
    assert.match(check({ plans: Array.from({ length: MAX_PLANS + 1 }, () => plan()) }).errors[0], /exceeds/);
  });

  it("rejects record fields, path fields, and any other unexpected key", () => {
    for (const key of ["record", "evidence", "title", "body", "path", "file", "cwd", "sources", "intent", "whatever"]) {
      assert.equal(check({ plans: [plan({ [key]: "x" })] }).ok, false, key);
    }
  });

  it("requires an eligible known cluster and enough distinct sources from it", () => {
    for (const bad of [
      plan({ clusterId: "g-unknown" }),
      plan({ clusterId: "g-inelig", provisionalSources: ["sx", "sy"] }),
      plan({ clusterId: "../g-aaa" }),
      plan({ provisionalSources: ["s1"] }),
      plan({ provisionalSources: ["s1", "s9"] }),
      plan({ provisionalSources: ["s1", "../s2"] }),
      plan({ provisionalSources: "s1,s2" }),
      plan({ provisionalCount: 3 }),
      plan({ kind: "delete" }),
      plan({ provisionalIntent: "" }),
      plan({ provisionalIntent: "x".repeat(501) }),
    ]) {
      assert.equal(check({ plans: [bad] }).ok, false, JSON.stringify(bad));
    }
    assert.equal(check({ plans: [plan()] }, 3).ok, false, "the floor applies to plan sources");
  });

  it("requires unique safe ids, and one bad plan rejects the whole reply", () => {
    for (const id of ["../e1", "a/b", ".hidden", "x".repeat(65)]) assert.equal(check({ plans: [plan({ id })] }).ok, false, id);
    assert.equal(check({ plans: [plan(), plan()] }).ok, false);
    const mixed = check({ plans: [plan({ id: "good" }), plan({ id: "bad", clusterId: "g-unknown" })] });
    assert.equal(mixed.ok, false);
    assert.deepEqual(mixed.plans, []);
    assert.match(mixed.errors.join(), /plans\[1\]/);
  });
});

describe("synthesize", () => {
  const soul = { text: "SOUL TEXT", sha256: "abc123" };
  const run = (invoke, extra = {}) =>
    synthesize(ledger(), { invoke, stateDir: tmpDir(), runId: "run-1", floor: 2, soul, evidenceIndex: evidenceIndex(), rejections: [], transcriptCount: 2, harnessSummary: "codex 2", runNote: "", ...extra });

  it("renders eligible evidence, SOUL, and prior rejections into an archived prompt", async () => {
    const stateDir = tmpDir();
    let prompt = "";
    await run(
      async (role, p) => {
        prompt = p;
        return { plans: [] };
      },
      { stateDir, rejections: [{ edit: "e3", clusterId: "g-old", title: "Old idea", sources: ["s1"], reason: "too-narrow" }] },
    );
    assert.ok(prompt.includes("[g-aaa] sessions=2"));
    assert.ok(!prompt.includes("g-inelig"));
    assert.ok(prompt.includes("SOUL TEXT") && prompt.includes("abc123"));
    assert.ok(prompt.includes("[e3] Old idea (cluster g-old"));
    assert.equal(fs.readFileSync(path.join(stateDir, "prompts", "run-1__synthesis.md"), "utf8"), prompt);
  });

  it("returns validated plans, or none with a note on failure or invalid output", async () => {
    assert.deepEqual((await run(async () => ({ plans: [plan()] }))).plans, [plan()]);
    const failed = await run(async () => {
      throw new Error("endpoint down");
    });
    assert.deepEqual([failed.plans, failed.failed], [[], true]);
    assert.match(failed.note, /synthesis failed \(endpoint down\)/);
    const invalid = await run(async () => ({ plans: [plan({ record: {} })] }));
    assert.equal(invalid.failed, true);
    assert.match(invalid.note, /plans invalid/);
    const empty = await run(async () => ({ plans: [] }));
    assert.deepEqual([empty.plans, empty.failed], [[], false]);
  });

  it("renders rejection rows, including those without identity", () => {
    assert.equal(renderRejections([]), "(none)");
    assert.match(renderRejections([{ reason: "other" }]), /^- rejected candidate \(reason other\)$/);
  });
});
