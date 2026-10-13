import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

import { renderPrompt, SELF_SESSION_SENTINEL } from "../src/prompts.js";
import {
  buildConsolidatePrompt,
  parseConsolidateResult,
  mergeClusters,
  consolidateLedger,
  renderGapEntries,
} from "../src/consolidate.js";
import { persistPrompt } from "../src/analyze.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CONSOLIDATE_MD = path.join(HERE, "..", "prompts", "consolidate.md");
const NOTICE = path.join(HERE, "..", "LICENSE.NOTICE");

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "ca-consolidate-"));
}

function ledgerWith(clusters) {
  return { version: 1, minGapEvidence: 2, clusters };
}

function cluster(overrides = {}) {
  return {
    id: "g-aaa",
    proposedInstruction: "Do X",
    representativeQuote: "quote-a",
    mistake: "mistake-a",
    sources: ["s1", "s2"],
    count: 2,
    eligible: true,
    perSource: {
      s1: { quote: "quote-a1", mistake: "mistake-a" },
      s2: { quote: "quote-a2", mistake: "mistake-a" },
    },
    ...overrides,
  };
}

describe("consolidate.md policy (Backpass src/prompts/consolidate.md @ 0268201)", () => {
  it("maps exact upstream provenance in LICENSE.NOTICE (prompt carries no license comments)", () => {
    const notice = fs.readFileSync(NOTICE, "utf8");
    assert.ok(notice.includes("Backpass"), "NOTICE must name Backpass");
    assert.ok(notice.includes("0268201"), "NOTICE must pin commit 0268201");
    assert.ok(notice.includes("src/prompts/consolidate.md"), "NOTICE must name upstream module");
    assert.ok(notice.includes("improve/prompts/consolidate.md"), "NOTICE must map the CA prompt file");
    assert.ok(
      notice.includes("https://github.com/kunchenguid/backpass"),
      "NOTICE must carry source URL",
    );
    const text = fs.readFileSync(CONSOLIDATE_MD, "utf8");
    assert.ok(!text.includes("Backpass"), "prompt body carries no license comments");
    assert.ok(!text.includes("0268201"), "prompt body carries no pinned commit");
  });

  it("declares exactly {{GAP_ENTRIES}} and nothing else", () => {
    const text = fs.readFileSync(CONSOLIDATE_MD, "utf8");
    const tokens = [...text.matchAll(/\{\{([A-Za-z0-9_]+)\}\}/g)].map((m) => m[1]);
    assert.deepEqual([...new Set(tokens)].sort(), ["GAP_ENTRIES"]);
  });

  it("does not bake in the sentinel", () => {
    const text = fs.readFileSync(CONSOLIDATE_MD, "utf8");
    assert.ok(!text.includes("ca-improve:self-session"));
  });

  it("states merge policy: same underlying gap, when unsure do not merge, unique membership, empty valid", () => {
    const text = fs.readFileSync(CONSOLIDATE_MD, "utf8");
    assert.ok(/same underlying gap/i.test(text));
    assert.ok(/when unsure, do not merge/i.test(text));
    assert.ok(/at most one group|one group/i.test(text));
    assert.ok(/\[\s*\]/.test(text) || /empty/i.test(text));
  });
});

describe("consolidate render + persistence (exact)", () => {
  it("renderPrompt keeps sentinel FIRST and renders GAP_ENTRIES", () => {
    const out = renderPrompt("consolidate", { GAP_ENTRIES: "[g-a] hi" });
    assert.ok(out.startsWith(`${SELF_SESSION_SENTINEL}\n`));
    assert.ok(out.includes("[g-a] hi"));
  });

  it("fails strict on missing/unused placeholders", () => {
    assert.throws(() => renderPrompt("consolidate", {}), /GAP_ENTRIES/);
    assert.throws(
      () => renderPrompt("consolidate", { GAP_ENTRIES: "x", EXTRA: "y" }),
      /EXTRA/,
    );
  });

  it("renderGapEntries names every eligible cluster id", () => {
    const text = renderGapEntries([cluster({ id: "g-1" }), cluster({ id: "g-2" })]);
    assert.ok(text.includes("g-1"));
    assert.ok(text.includes("g-2"));
  });

  it("persists rendered consolidate prompt privately with run/stage metadata", () => {
    const stateDir = tmpDir();
    const runId = "run-CON1";
    const prompt = buildConsolidatePrompt(ledgerWith([cluster()]));
    const file = persistPrompt(stateDir, {
      runId,
      transcriptId: "consolidate",
      harness: "stage",
      prompt,
      stage: "consolidate",
    });
    assert.ok(file.endsWith(`${runId}__consolidate.md`));
    assert.ok(fs.readFileSync(file, "utf8").startsWith(`${SELF_SESSION_SENTINEL}\n`));
    const meta = JSON.parse(
      fs.readFileSync(path.join(stateDir, "prompts", `${runId}__consolidate.json`), "utf8"),
    );
    assert.equal(meta.runId, runId);
    assert.equal(meta.stage, "consolidate");
    if (process.platform !== "win32") {
      assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    }
  });
});

describe("consolidate parse/validate JSON groups", () => {
  const base = ledgerWith([
    cluster({ id: "g-a", sources: ["s1", "s2"] }),
    cluster({ id: "g-b", sources: ["s3", "s4"] }),
    cluster({ id: "g-c", sources: ["s5", "s6"] }),
  ]);

  it("accepts a well-formed group of existing ids", () => {
    const groups = parseConsolidateResult({ merges: [["g-a", "g-b"]] }, base);
    assert.deepEqual(groups, [["g-a", "g-b"]]);
  });

  it("drops groups with unknown ids and malformed shapes", () => {
    assert.deepEqual(parseConsolidateResult({ merges: [["g-a", "g-nope"]] }, base), []);
    assert.deepEqual(parseConsolidateResult({ merges: [["g-a"]] }, base), []);
    assert.deepEqual(parseConsolidateResult({ merges: ["g-a"] }, base), []);
    assert.deepEqual(parseConsolidateResult({ merges: [] }, base), []);
    assert.deepEqual(parseConsolidateResult({}, base), []);
    assert.deepEqual(parseConsolidateResult(null, base), []);
  });

  it("dedupes within a group and enforces unique membership across groups", () => {
    const groups = parseConsolidateResult(
      { merges: [["g-a", "g-a", "g-b"], ["g-b", "g-c"]] },
      base,
    );
    assert.deepEqual(groups, [["g-a", "g-b"]]);
  });

  it("refuses non-string ids", () => {
    assert.deepEqual(parseConsolidateResult({ merges: [[null, 42]] }, base), []);
  });
});

describe("consolidate mechanical merge", () => {
  it("unions distinct sessions and preserves per-source quote provenance", () => {
    const led = ledgerWith([
      cluster({ id: "g-a", sources: ["s1", "s2"], perSource: { s1: { quote: "qa1", mistake: "m" } } }),
      cluster({ id: "g-b", sources: ["s2", "s3"], perSource: { s3: { quote: "qb3", mistake: "m" } } }),
    ]);
    const merged = mergeClusters(led, [["g-a", "g-b"]], { minGapEvidence: 2 });
    assert.equal(merged.clusters.length, 1);
    assert.deepEqual(merged.clusters[0].sources, ["s1", "s2", "s3"]);
    assert.equal(merged.clusters[0].count, 3);
    assert.equal(merged.clusters[0].perSource.s1.quote, "qa1");
    assert.equal(merged.clusters[0].perSource.s3.quote, "qb3");
    assert.ok(merged.clusters[0].eligible);
  });

  it("never double-counts a session shared by both entries", () => {
    const led = ledgerWith([
      cluster({ id: "g-a", sources: ["s1"] }),
      cluster({ id: "g-b", sources: ["s1"] }),
    ]);
    const merged = mergeClusters(led, [["g-a", "g-b"]], { minGapEvidence: 2 });
    assert.deepEqual(merged.clusters[0].sources, ["s1"]);
    assert.equal(merged.clusters[0].count, 1);
  });
});

describe("review findings: provenance + eligible-only validation", () => {
  it("RED: same source different quotes are all preserved on merge", () => {
    const led = ledgerWith([
      cluster({ id: "g-a", proposedInstruction: "Do X", representativeQuote: "qa1", mistake: "ma", sources: ["s1", "s2"], perSource: { s1: { quote: "qa1", mistake: "ma" }, s2: { quote: "qa2", mistake: "ma" } } }),
      cluster({ id: "g-b", proposedInstruction: "Do X now", representativeQuote: "qb1", mistake: "ma", sources: ["s1", "s3"], perSource: { s1: { quote: "qb1-different", mistake: "ma" }, s3: { quote: "qb3", mistake: "ma" } } }),
    ]);
    const merged = mergeClusters(led, [["g-a", "g-b"]], { minGapEvidence: 2 });
    const mc = merged.clusters[0];
    // Both same-source sightings must stay retrievable (first-wins perSource
    // plus explicit variant provenance), not silently overwritten.
    const variants = (mc.quoteProvenance || []).filter((q) => q.source === "s1").map((q) => q.quote);
    assert.ok(variants.includes("qa1"), "first same-source quote survives");
    assert.ok(variants.includes("qb1-different"), "conflicting same-source quote survives");
  });

  it("RED: canonical instruction/quote/mistake come from one member", () => {
    const led = ledgerWith([
      cluster({ id: "g-a", proposedInstruction: "Do X", representativeQuote: "quote-a", mistake: "mistake-a", sources: ["s1", "s2"] }),
      cluster({ id: "g-b", proposedInstruction: "Do X thoroughly and carefully every time", representativeQuote: "quote-b", mistake: "mistake-b", sources: ["s3", "s4", "s5"] }),
    ]);
    const mc = mergeClusters(led, [["g-a", "g-b"]], { minGapEvidence: 2 }).clusters[0];
    assert.equal(mc.proposedInstruction, "Do X");
    assert.equal(mc.representativeQuote, "quote-a");
    assert.equal(mc.mistake, "mistake-a");
  });

  it("RED: merges validate against every exact ID shown in the prompt (singletons included)", () => {
    const led = ledgerWith([
      cluster({ id: "g-a", sources: ["s1", "s2"], eligible: true }),
      cluster({ id: "g-b", sources: ["s3", "s4"], eligible: true }),
      cluster({ id: "g-x", sources: ["s9"], eligible: false }),
    ]);
    assert.deepEqual(parseConsolidateResult({ merges: [["g-a", "g-x"]] }, led), [["g-a", "g-x"]]);
    assert.deepEqual(parseConsolidateResult({ merges: [["g-a", "g-b"]] }, led), [["g-a", "g-b"]]);
    assert.deepEqual(parseConsolidateResult({ merges: [["g-a", "g-nope"]] }, led), []);
  });
});

describe("singleton actual gaps via consolidation merge (RED)", () => {
  function singleton(overrides = {}) {
    return cluster({
      sources: ["s1"],
      count: 1,
      eligible: false,
      ...overrides,
    });
  }

  it("two distinct singleton actual gaps merged in the same run become eligible", () => {
    const led = ledgerWith([
      singleton({
        id: "g-single-a",
        proposedInstruction: "Bootstrap context once",
        representativeQuote: "sessions re-derive project context from scratch",
        mistake: "sessions re-derive project context from scratch",
        sources: ["s1"],
        perSource: { s1: { quote: "sessions re-derive project context from scratch", mistake: "m-a" } },
      }),
      singleton({
        id: "g-single-b",
        proposedInstruction: "Bootstrap context once",
        representativeQuote: "sessions rebuild context every time",
        mistake: "sessions rebuild context every time",
        sources: ["s2"],
        perSource: { s2: { quote: "sessions rebuild context every time", mistake: "m-b" } },
      }),
    ]);
    let seenClusters = null;
    let seenPrompt = null;
    const out = consolidateLedger(led, {
      invoke: (args) => {
        seenClusters = args.clusters;
        seenPrompt = args.prompt;
        return { status: "ok", result: { merges: [["g-single-a", "g-single-b"]] } };
      },
      minGapEvidence: 2,
    });
    assert.ok(seenClusters, "consolidation must be submitted (not gated before ACPX)");
    assert.equal(seenClusters.length, 2, "ALL open clusters must be submitted before eligibility gating");
    assert.ok(seenPrompt.includes("g-single-a") && seenPrompt.includes("g-single-b"));
    assert.equal(out.ledger.clusters.length, 1);
    assert.deepEqual(out.ledger.clusters[0].sources, ["s1", "s2"]);
    assert.equal(out.ledger.clusters[0].count, 2);
    assert.ok(out.ledger.clusters[0].eligible, "merged distinct sessions reach the floor");
    assert.equal(out.ledger.clusters[0].perSource.s1.quote, "sessions re-derive project context from scratch");
    assert.equal(out.ledger.clusters[0].perSource.s2.quote, "sessions rebuild context every time");
  });

  it("parse validates against every exact cluster ID presented to the prompt", () => {
    const led = ledgerWith([
      singleton({ id: "g-single-a", sources: ["s1"] }),
      singleton({ id: "g-single-b", sources: ["s2"] }),
    ]);
    assert.deepEqual(
      parseConsolidateResult({ merges: [["g-single-a", "g-single-b"]] }, led),
      [["g-single-a", "g-single-b"]],
    );
    assert.deepEqual(parseConsolidateResult({ merges: [["g-single-a", "g-nope"]] }, led), []);
  });
});

describe("consolidateLedger orchestration (acpx-only, fail-soft)", () => {
  it("skips acpx when fewer than 2 open clusters (no invoke call)", () => {
    let called = 0;
    const led = ledgerWith([cluster({ id: "g-a", eligible: false, sources: ["s1"], count: 1 })]);
    const out = consolidateLedger(led, {
      invoke: () => {
        called += 1;
        return { status: "ok", merges: [] };
      },
      minGapEvidence: 2,
    });
    assert.equal(called, 0);
    assert.ok(out.skipped);
    assert.deepEqual(out.ledger, led);
  });

  it("skips acpx when analyzer is mock (deterministic lexical current result)", () => {
    let called = 0;
    const led = ledgerWith([cluster({ id: "g-a" }), cluster({ id: "g-b" })]);
    const out = consolidateLedger(led, {
      invoke: () => {
        called += 1;
        return { status: "ok", merges: [] };
      },
      analyzer: "mock",
      minGapEvidence: 2,
    });
    assert.equal(called, 0);
    assert.ok(out.skipped);
  });

  it("merges on valid acpx groups and persists prompt with run/stage metadata", () => {
    const stateDir = tmpDir();
    const led = ledgerWith([
      cluster({ id: "g-a", sources: ["s1"] }),
      cluster({ id: "g-b", sources: ["s2"] }),
    ]);
    const out = consolidateLedger(led, {
      invoke: () => ({ status: "ok", merges: [["g-a", "g-b"]] }),
      stateDir,
      runId: "run-CM",
      minGapEvidence: 2,
    });
    assert.equal(out.ledger.clusters.length, 1);
    assert.equal(out.merged, 1);
    assert.ok(fs.existsSync(path.join(stateDir, "prompts", "run-CM__consolidate.md")));
    const meta = JSON.parse(
      fs.readFileSync(path.join(stateDir, "prompts", "run-CM__consolidate.json"), "utf8"),
    );
    assert.equal(meta.stage, "consolidate");
  });

  it("falls back to lexical current result with a visible note on acpx failure", () => {
    const led = ledgerWith([cluster({ id: "g-a" }), cluster({ id: "g-b" })]);
    const out = consolidateLedger(led, {
      invoke: () => ({ status: "failed", error: "boom" }),
      minGapEvidence: 2,
    });
    assert.deepEqual(out.ledger, led);
    assert.ok(out.failed);
    assert.ok(/lexical|consolidation failed/i.test(out.note));
  });

  it("falls back with a visible note on invalid/unparseable acpx output", () => {
    const led = ledgerWith([cluster({ id: "g-a" }), cluster({ id: "g-b" })]);
    const out = consolidateLedger(led, {
      invoke: () => ({ status: "ok", merges: "not-an-array" }),
      minGapEvidence: 2,
    });
    assert.deepEqual(out.ledger, led);
    assert.ok(out.failed);
    assert.ok(typeof out.note === "string" && out.note.length > 0);
  });

  it("makes no real acpx calls in tests (injectable invoke only)", () => {
    const led = ledgerWith([cluster({ id: "g-a" }), cluster({ id: "g-b" })]);
    const out = consolidateLedger(led, {
      invoke: ({ prompt }) => {
        assert.ok(prompt.includes("ca-improve:self-session"));
        return { status: "ok", merges: [] };
      },
    });
    assert.ok(Array.isArray(out.ledger.clusters));
  });
});
