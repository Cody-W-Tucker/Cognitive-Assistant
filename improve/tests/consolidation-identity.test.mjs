import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { foldEvidence } from "../src/fold.js";
import {
  consolidateLedger,
  corroborateOpenGaps,
  loadOpenGaps,
} from "../src/consolidate.js";

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "ca-gap-identity-"));
}

function singleton(overrides = {}) {
  return {
    id: "g-x",
    proposedInstruction: "Bootstrap context once",
    representativeQuote: "quote",
    mistake: "mistake",
    sources: ["s1"],
    count: 1,
    eligible: false,
    perSource: { s1: { quote: "quote", mistake: "mistake" } },
    ...overrides,
  };
}

describe("gap identity: same instruction + unrelated quotes must NOT corroborate", () => {
  it("same generic instruction across unrelated quotes/sessions with zero merges stays ineligible", () => {
    const stateDir = tmpDir();
    const first = {
      version: 1,
      minGapEvidence: 2,
      clusters: [
        singleton({
          id: "g-alpha",
          proposedInstruction: "Bootstrap context once",
          representativeQuote: "alpha unrelated quote about startup context",
          mistake: "alpha unrelated mistake about startup context",
          sources: ["s1"],
          perSource: {
            s1: { quote: "alpha unrelated quote about startup context", mistake: "alpha unrelated mistake about startup context" },
          },
        }),
      ],
    };
    consolidateLedger(first, { analyzer: "mock", stateDir, minGapEvidence: 2 });

    const second = {
      version: 1,
      minGapEvidence: 2,
      clusters: [
        singleton({
          id: "g-beta",
          proposedInstruction: "Bootstrap context once",
          representativeQuote: "beta unrelated quote about retry backoff",
          mistake: "beta unrelated mistake about retry backoff",
          sources: ["s2"],
          perSource: {
            s2: { quote: "beta unrelated quote about retry backoff", mistake: "beta unrelated mistake about retry backoff" },
          },
        }),
      ],
    };
    const out = consolidateLedger(second, { analyzer: "mock", stateDir, minGapEvidence: 2 });
    const found = out.ledger.clusters.find((c) => c.id === "g-beta");
    assert.ok(found, "distinct singleton must remain");
    assert.equal(found.eligible, false, "same instruction with unrelated quotes must not become eligible");
    assert.ok(!found.corroboratedOpenGap, "no open-gap corroboration across distinct observations");
    assert.deepEqual([...found.sources].sort(), ["s2"], "sources must not union across distinct observations");
  });

  it("same-run distinct singletons with same instruction but unrelated quotes stay distinct on zero merges", () => {
    const led = {
      version: 1,
      minGapEvidence: 2,
      clusters: [
        singleton({
          id: "g-a1",
          proposedInstruction: "Bootstrap context once",
          representativeQuote: "alpha unrelated quote about startup context",
          mistake: "alpha unrelated mistake",
          sources: ["s1"],
          perSource: { s1: { quote: "alpha unrelated quote about startup context", mistake: "alpha unrelated mistake" } },
        }),
        singleton({
          id: "g-b1",
          proposedInstruction: "Bootstrap context once",
          representativeQuote: "beta unrelated quote about retry backoff",
          mistake: "beta unrelated mistake",
          sources: ["s2"],
          perSource: { s2: { quote: "beta unrelated quote about retry backoff", mistake: "beta unrelated mistake" } },
        }),
      ],
    };
    const out = consolidateLedger(led, {
      invoke: () => ({ status: "ok", result: { merges: [] } }),
      minGapEvidence: 2,
    });
    assert.equal(out.ledger.clusters.length, 2, "no valid merges means singletons stay distinct");
    for (const c of out.ledger.clusters) {
      assert.equal(c.eligible, false, `${c.id} must stay ineligible`);
      assert.ok(!c.corroboratedOpenGap, `${c.id} must not be marked corroborated`);
    }
  });

  it("corroborateOpenGaps never keys on proposedInstruction alone", () => {
    const persisted = {
      version: 1,
      gaps: [
        {
          id: "g-old",
          key: "alpha unrelated quote about startup context",
          proposedInstruction: "Bootstrap context once",
          representativeQuote: "alpha unrelated quote about startup context",
          mistake: "alpha unrelated mistake",
          sources: ["s1"],
          count: 1,
          eligible: false,
        },
      ],
    };
    const ledger = {
      version: 1,
      minGapEvidence: 2,
      clusters: [
        singleton({
          id: "g-new",
          proposedInstruction: "Bootstrap context once",
          representativeQuote: "beta unrelated quote about retry backoff",
          mistake: "beta unrelated mistake",
          sources: ["s2"],
          perSource: { s2: { quote: "beta unrelated quote about retry backoff", mistake: "beta unrelated mistake" } },
        }),
      ],
    };
    const out = corroborateOpenGaps(ledger, persisted, { minGapEvidence: 2 });
    const found = out.clusters.find((c) => c.id === "g-new");
    assert.equal(found.eligible, false);
    assert.ok(!found.corroboratedOpenGap);
    assert.deepEqual(found.sources, ["s2"]);
  });
});

describe("gap identity: exact same observation across sessions is eligible", () => {
  it("fold groups only the exact normalized quote/mistake, ignoring instruction text", () => {
    const folded = foldEvidence(
      [
        {
          transcriptId: "s1",
          status: "ok",
          gaps: [{ quote: "sessions re-derive project context from scratch", mistake: "m1", proposedInstruction: "Bootstrap context once" }],
        },
        {
          transcriptId: "s2",
          status: "ok",
          gaps: [{ quote: "sessions re-derive project context from scratch", mistake: "m1", proposedInstruction: "Totally different wording here" }],
        },
        {
          transcriptId: "s3",
          status: "ok",
          gaps: [{ quote: "an unrelated retry backoff observation", mistake: "m2", proposedInstruction: "Bootstrap context once" }],
        },
      ],
      { minGapEvidence: 2 },
    );
    assert.equal(folded.clusters.length, 2, "same exact quote groups; unrelated quote stays separate despite same instruction");
    const hit = folded.clusters.find((c) => c.representativeQuote === "sessions re-derive project context from scratch");
    assert.ok(hit, "exact observation cluster exists");
    assert.deepEqual([...hit.sources].sort(), ["s1", "s2"]);
    assert.ok(hit.eligible, "exact identity across 2 sessions meets the floor");
    const miss = folded.clusters.find((c) => c.representativeQuote === "an unrelated retry backoff observation");
    assert.ok(miss && !miss.eligible, "unrelated quote stays a singleton even with the same instruction");
  });

  it("persisted exact observation corroborates a repeat across runs", () => {
    const stateDir = tmpDir();
    const quote = "sessions re-derive project context from scratch";
    const first = {
      version: 1,
      minGapEvidence: 2,
      clusters: [singleton({ id: "g-same", representativeQuote: quote, mistake: quote, sources: ["s1"], perSource: { s1: { quote, mistake: quote } } })],
    };
    consolidateLedger(first, { analyzer: "mock", stateDir, minGapEvidence: 2 });
    const second = {
      version: 1,
      minGapEvidence: 2,
      clusters: [singleton({ id: "g-same", representativeQuote: quote, mistake: quote, sources: ["s2"], perSource: { s2: { quote, mistake: quote } } })],
    };
    const out = consolidateLedger(second, { analyzer: "mock", stateDir, minGapEvidence: 2 });
    const found = out.ledger.clusters.find((c) => c.id === "g-same");
    assert.ok(found.eligible, "same exact gap identity across sessions becomes eligible");
    assert.ok(found.corroboratedOpenGap, "repeat is marked corroborated");
    assert.deepEqual([...found.sources].sort(), ["s1", "s2"]);
    assert.equal(found.perSource.s1.quote, quote, "source-backed quote provenance preserved");
    assert.equal(found.perSource.s2.quote, quote);
  });
});

describe("gap identity: ACPX-validated paraphrase merge is persisted and reusable", () => {
  it("validated merge promotes paraphrase singletons and persists member IDs/provenance", () => {
    const stateDir = tmpDir();
    const led = {
      version: 1,
      minGapEvidence: 2,
      clusters: [
        singleton({
          id: "g-p1",
          proposedInstruction: "Bootstrap context once",
          representativeQuote: "sessions re-derive project context from scratch",
          mistake: "sessions re-derive project context from scratch",
          sources: ["s1"],
          perSource: { s1: { quote: "sessions re-derive project context from scratch", mistake: "m" } },
        }),
        singleton({
          id: "g-p2",
          proposedInstruction: "Bootstrap context once, differently worded",
          representativeQuote: "sessions rebuild context every time",
          mistake: "sessions rebuild context every time",
          sources: ["s2"],
          perSource: { s2: { quote: "sessions rebuild context every time", mistake: "m" } },
        }),
      ],
    };
    const out = consolidateLedger(led, {
      invoke: () => ({ status: "ok", result: { merges: [["g-p1", "g-p2"]] } }),
      stateDir,
      runId: "run-PARA1",
      minGapEvidence: 2,
    });
    assert.equal(out.ledger.clusters.length, 1, "validated paraphrases merge");
    const merged = out.ledger.clusters[0];
    assert.ok(merged.eligible, "merged distinct sessions reach the floor");
    assert.deepEqual([...merged.sources].sort(), ["s1", "s2"]);
    assert.ok(Array.isArray(merged.mergedFrom) && merged.mergedFrom.includes("g-p1") && merged.mergedFrom.includes("g-p2"), "member IDs persisted on the cluster");
    assert.equal(merged.perSource.s1.quote, "sessions re-derive project context from scratch");
    assert.equal(merged.perSource.s2.quote, "sessions rebuild context every time");

    const persisted = loadOpenGaps(stateDir);
    const saved = persisted.gaps.find((g) => (merged.mergedFrom || []).includes(String(g.id)) || String(g.id) === String(merged.id));
    assert.ok(saved, "merged gap is persisted");
    const blob = JSON.stringify(saved);
    assert.ok(blob.includes("g-p1") && blob.includes("g-p2"), "persisted entry carries member IDs for safe reuse");
    assert.ok(
      blob.includes("sessions re-derive project context from scratch") && blob.includes("sessions rebuild context every time"),
      "persisted entry carries per-member quote provenance",
    );
  });
});
