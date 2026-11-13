import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import { consolidateLedger, corroborateOpenGaps, loadOpenGaps, mergeClusters, parseConsolidateResult, saveOpenGaps } from "../src/consolidate.js";
import { foldEvidence } from "../src/fold.js";
import { tmpDir } from "./helpers.mjs";

function cluster(overrides = {}) {
  const quote = overrides.representativeQuote || `quote for ${overrides.id || "g-x"}`;
  const sources = overrides.sources || ["s1"];
  return {
    id: "g-x",
    proposedInstruction: "Bootstrap context once",
    representativeQuote: quote,
    mistake: quote,
    sources,
    count: sources.length,
    eligible: sources.length >= 2,
    perSource: Object.fromEntries(sources.map((s) => [s, { quote, mistake: quote }])),
    ...overrides,
  };
}

const ledgerOf = (...clusters) => ({ version: 1, minGapEvidence: 2, clusters });
const replying = (reply) => async () => reply;

/** One run's consolidation, saving open gaps as the pipeline does. */
async function consolidate(ledger, { stateDir = tmpDir(), invoke = replying({ merges: [] }) } = {}) {
  const out = await consolidateLedger(ledger, { invoke, stateDir, runId: "run-1", minGapEvidence: 2 });
  saveOpenGaps(stateDir, out.openGaps);
  return out;
}

describe("merge groups from the model", () => {
  const led = ledgerOf(cluster({ id: "g-a", sources: ["s1", "s2"] }), cluster({ id: "g-b", sources: ["s3", "s4"] }), cluster({ id: "g-x", sources: ["s9"] }));

  it("accepts groups of known ids shown in the prompt, singletons included", () => {
    assert.deepEqual(parseConsolidateResult({ merges: [["g-a", "g-x"]] }, led), [["g-a", "g-x"]]);
    assert.deepEqual(parseConsolidateResult({ merges: [[" g-a ", "g-b"]] }, led), [["g-a", "g-b"]]);
  });

  it("drops unknown ids, malformed groups, non-string ids, duplicates, and repeat claims", () => {
    assert.deepEqual(parseConsolidateResult({ merges: [["g-a", "g-nope"]] }, led), []);
    assert.deepEqual(parseConsolidateResult({ merges: ["g-a", null, [1, 2]] }, led), []);
    assert.deepEqual(parseConsolidateResult({ merges: [["g-a", "g-a", "g-b"], ["g-b", "g-x"]] }, led), [["g-a", "g-b"]]);
    assert.deepEqual(parseConsolidateResult({ groups: [] }, led), []);
  });
});

describe("mechanical merge", () => {
  it("unions distinct sessions without double counting and keeps every per-source quote", () => {
    const merged = mergeClusters(
      ledgerOf(
        cluster({ id: "g-a", sources: ["s1", "s2"], perSource: { s1: { quote: "qa1", mistake: "m" }, s2: { quote: "qa2", mistake: "m" } } }),
        cluster({ id: "g-b", sources: ["s1", "s3"], perSource: { s1: { quote: "qb1", mistake: "m" }, s3: { quote: "qb3", mistake: "m" } } }),
      ),
      [["g-a", "g-b"]],
    ).clusters;
    assert.equal(merged.length, 1);
    assert.deepEqual(merged[0].sources, ["s1", "s2", "s3"]);
    assert.equal(merged[0].count, 3);
    assert.equal(merged[0].perSource.s1.quote, "qa1", "first sighting per source wins");
    assert.deepEqual(merged[0].quoteProvenance.filter((q) => q.source === "s1").map((q) => q.quote), ["qa1", "qb1"]);
    assert.deepEqual(merged[0].mergedFrom, ["g-a", "g-b"]);
  });

  it("takes instruction, quote, and mistake together from one member", () => {
    const [mc] = mergeClusters(
      ledgerOf(
        cluster({ id: "g-a", proposedInstruction: "Do X", representativeQuote: "quote-a", mistake: "mistake-a", sources: ["s1"] }),
        cluster({ id: "g-b", proposedInstruction: "Do X thoroughly every time", representativeQuote: "quote-b", mistake: "mistake-b", sources: ["s3"] }),
      ),
      [["g-a", "g-b"]],
    ).clusters;
    assert.deepEqual([mc.proposedInstruction, mc.representativeQuote, mc.mistake, mc.eligible], ["Do X", "quote-a", "mistake-a", true]);
  });
});

describe("consolidateLedger", () => {
  it("skips the model with fewer than two clusters", async () => {
    let calls = 0;
    const out = await consolidate(ledgerOf(cluster({ id: "g-a" })), {
      invoke: async () => {
        calls += 1;
      },
    });
    assert.equal(calls, 0);
    assert.match(out.note, /fewer than two open gaps/);
  });

  it("merges valid groups, promoting distinct-session singletons, and archives the prompt", async () => {
    const stateDir = tmpDir();
    const out = await consolidate(ledgerOf(cluster({ id: "g-a", sources: ["s1"] }), cluster({ id: "g-b", sources: ["s2"] })), {
      stateDir,
      invoke: replying({ merges: [["g-a", "g-b"]] }),
    });
    assert.equal(out.ledger.clusters.length, 1);
    assert.equal(out.ledger.clusters[0].eligible, true);
    assert.equal(out.merged, 1);
    assert.match(out.note, /merged 1 group/);
    assert.ok(fs.existsSync(path.join(stateDir, "prompts", "run-1__consolidate.md")));
  });

  it("falls back to exact identity with a note when the model fails or returns junk", async () => {
    const led = ledgerOf(cluster({ id: "g-a" }), cluster({ id: "g-b", sources: ["s2"] }));
    for (const invoke of [
      async () => {
        throw new Error("endpoint down");
      },
      replying({ verdict: "merge everything" }),
      replying({ merges: [["g-a", "g-unknown"]] }),
    ]) {
      const out = await consolidate(led, { invoke });
      assert.equal(out.ledger.clusters.length, 2);
      assert.equal(out.merged, 0);
      assert.match(out.note, /continuing with exact observation identity/);
    }
  });

  it("rejects an invalid evidence floor", async () => {
    for (const bad of [1, 0, 2.5, "x"]) {
      await assert.rejects(consolidateLedger(ledgerOf(), { invoke: replying({}), stateDir: tmpDir(), runId: "r", minGapEvidence: bad }), /integer >= 2/);
      assert.throws(() => mergeClusters(ledgerOf(), [], { minGapEvidence: bad }), /integer >= 2/);
      assert.throws(() => foldEvidence([], { minGapEvidence: bad }), /integer >= 2/);
    }
  });
});

describe("gap identity across runs", () => {
  it("fold groups only the exact normalized observation, ignoring instruction text", () => {
    const q = "sessions re-derive project context from scratch";
    const folded = foldEvidence([
      { transcriptId: "s1", status: "ok", gaps: [{ quote: q, mistake: "m1", proposedInstruction: "Bootstrap" }] },
      { transcriptId: "s2", status: "ok", gaps: [{ quote: `  ${q.toUpperCase()} `, mistake: "m1", proposedInstruction: "Different wording" }] },
      { transcriptId: "s3", status: "ok", gaps: [{ quote: "an unrelated observation", mistake: "m2", proposedInstruction: "Bootstrap" }] },
      { transcriptId: "s4", status: "failed", gaps: [{ quote: q }] },
    ]);
    const hit = folded.clusters.find((c) => c.representativeQuote === q);
    assert.deepEqual(hit.sources, ["s1", "s2"]);
    assert.equal(hit.eligible, true);
    assert.equal(folded.clusters.find((c) => c.representativeQuote === "an unrelated observation").eligible, false);
  });

  it("the same observation in a later run corroborates and becomes eligible", async () => {
    const stateDir = tmpDir();
    await consolidate(ledgerOf(cluster({ id: "g-same", representativeQuote: "same gap", sources: ["s1"] })), { stateDir });
    const out = await consolidate(ledgerOf(cluster({ id: "g-same", representativeQuote: "same gap", sources: ["s2"] })), { stateDir });
    const [c] = out.ledger.clusters;
    assert.deepEqual(c.sources, ["s1", "s2"]);
    assert.equal(c.eligible, true);
    assert.equal(c.corroboratedOpenGap, true);
    assert.equal(c.openGapPromotedSingleton, true);
    assert.equal(c.perSource.s1.quote, "same gap");
    assert.match(out.note, /open-gap corroboration/);
  });

  it("the same instruction over unrelated observations never corroborates", async () => {
    const stateDir = tmpDir();
    await consolidate(ledgerOf(cluster({ id: "g-alpha", representativeQuote: "alpha startup context", sources: ["s1"] })), { stateDir });
    const out = await consolidate(ledgerOf(cluster({ id: "g-beta", representativeQuote: "beta retry backoff", sources: ["s2"] })), { stateDir });
    const beta = out.ledger.clusters.find((c) => c.id === "g-beta");
    assert.equal(beta.eligible, false);
    assert.equal(beta.corroboratedOpenGap, undefined);
    assert.deepEqual(beta.sources, ["s2"]);
    const direct = corroborateOpenGaps(ledgerOf(cluster({ id: "g-gamma", representativeQuote: "alpha startup context ", sources: ["s3"] })), loadOpenGaps(stateDir));
    assert.deepEqual(direct.clusters[0].sources, ["s1", "s3"], "matching is on observation text, not cluster id");
  });

  it("a model-validated paraphrase merge persists its members and corroborates a later paraphrase", async () => {
    const stateDir = tmpDir();
    const out = await consolidate(
      ledgerOf(cluster({ id: "g-p1", representativeQuote: "sessions re-derive context", sources: ["s1"] }), cluster({ id: "g-p2", representativeQuote: "sessions rebuild context", sources: ["s2"] })),
      { stateDir, invoke: replying({ merges: [["g-p1", "g-p2"]] }) },
    );
    assert.deepEqual(out.ledger.clusters[0].mergedFrom, ["g-p1", "g-p2"]);
    const saved = loadOpenGaps(stateDir).gaps.find((g) => g.id === out.ledger.clusters[0].id);
    assert.deepEqual(saved.memberIds, ["g-p1", "g-p2"]);
    assert.ok(saved.memberKeys.includes("sessions rebuild context"));

    const later = await consolidate(ledgerOf(cluster({ id: "g-new", representativeQuote: "Sessions  rebuild context", sources: ["s3"] })), { stateDir });
    assert.ok(later.ledger.clusters[0].sources.includes("s3"));
    assert.equal(later.ledger.clusters[0].eligible, true);
    assert.equal(later.ledger.clusters[0].corroboratedOpenGap, true);
  });
});
