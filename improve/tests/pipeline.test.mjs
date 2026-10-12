import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

import { runPipeline } from "../src/pipeline.js";
import { synthesizeWithAcpx } from "../src/synthesize.js";
import { consolidateLedger } from "../src/consolidate.js";
import { buildMockFinalAnnotation } from "../src/annotate.js";

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "ca-pipe-"));
}

function homeWithTranscripts(n = 2) {
  const home = tmpDir();
  const dir = path.join(home, ".codex", "sessions");
  fs.mkdirSync(dir, { recursive: true });
  for (let i = 0; i < n; i += 1) {
    const payload = JSON.stringify({ role: "user", text: `bootstrap context please ${i}` });
    fs.writeFileSync(path.join(dir, `2026-01-0${i + 1}T00-00-00Z.jsonl`), `${payload}\n`, "utf8");
  }
  return home;
}

const GAP_QUOTE = "sessions re-derive project context from scratch";
const GAP_QUOTE_B = "sessions never record why a fix was chosen";

/** Same gap sightings for every trace so the fold floor is met twice. */
function gapEvidence() {
  const gap = (quote) => ({
    proposedInstruction: quote === GAP_QUOTE ? "Bootstrap context once" : "Record why a fix was chosen",
    mistake: quote,
    quote,
    recurrenceRisk: "every new session pays the same cost",
  });
  return { status: "ok", positive: [], negative: [], gaps: [gap(GAP_QUOTE), gap(GAP_QUOTE_B)] };
}

/** Build a strictly valid NARROW plan from the actual folded ledger. */
function planForLedger(ledger) {
  const cluster = (ledger?.clusters || []).find((c) => c.eligible);
  assert.ok(cluster, "ledger must hold an eligible cluster");
  assert.ok(cluster.sources.length >= 2);
  return {
    clusterId: cluster.id,
    provisionalIntent: cluster.proposedInstruction,
    provisionalSources: [...cluster.sources],
  };
}

/** Build a strictly valid ANNOTATION final for one plan. */
function finalAnnotationForPlan(plan, ledger, evidenceIndex) {
  return buildMockFinalAnnotation(
    { id: "e1", kind: "add", ...plan },
    { ledger, evidenceIndex },
  );
}

describe("pipeline production wiring (injectable invokes, no real acpx)", () => {
  it("production success persists prompts + proposal notes with injected invokes (annotate owns finals)", async () => {
    const home = homeWithTranscripts(2);
    const stateDir = tmpDir();
    const proposal = await runPipeline({
      home,
      stateDir,
      analyzer: "acpx",
      runId: "run-PIPE1",
      analyzeInvoke: () => ({ status: "ok", evidence: gapEvidence() }),
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
      synthesizeInvoke: ({ ledger }) => ({ status: "ok", result: { plans: [planForLedger(ledger)] } }),
      annotateInvoke: (args) => {
        if (args?.stage === "annotate-preface") return { status: "ok", ready: true };
        const plans = args?.staged || [];
        // Production invoke supplies complete finals; the test double builds
        // them from the staged plans without inventing sessions.
        return {
          status: "ok",
          annotations: plans.map((p, i) => ({
            id: p.id || `e${i + 1}`,
            verdict: "keep",
            reason: String(p.provisionalIntent || "keep"),
            record: {
              id: `exp-test-${i}`,
              title: String(p.provisionalIntent),
              body: `Recurring gap: ${p.provisionalIntent}`,
              clusterId: String(p.clusterId),
              sources: [...p.provisionalSources],
              evidence: p.provisionalSources.map((source) => ({
                polarity: "negative",
                text: GAP_QUOTE,
                source,
                effect: GAP_QUOTE,
              })),
              counterevidence: "none observed",
              compilerImplication: "compiler appends this record to the experience block",
            },
          })),
        };
      },
    });
    assert.equal(proposal.edits.length, 1);
    assert.ok(proposal.edits[0].annotation && proposal.edits[0].annotation.verdict === "keep");
    assert.ok(proposal.edits[0].record && proposal.edits[0].record.title.length > 0);
    assert.ok(fs.existsSync(path.join(stateDir, "prompts", "run-PIPE1__consolidate.md")));
    assert.ok(fs.existsSync(path.join(stateDir, "prompts", "run-PIPE1__synthesis.md")));
    assert.ok(Array.isArray(proposal.notes));
    assert.equal(proposal.synthesis.failed, false);
  });

  it("mock follows the same plan->measure->preface->annotate-final path (annotation builds finals)", async () => {
    const home = homeWithTranscripts(2);
    const stateDir = tmpDir();
    const proposal = await runPipeline({
      home,
      stateDir,
      analyzer: "mock",
      runId: "run-MOCK1",
      analyzeInvoke: () => ({ status: "ok", evidence: gapEvidence() }),
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
    });
    assert.ok(proposal.edits.length >= 1);
    for (const edit of proposal.edits) {
      assert.equal(edit.annotation.verdict, "keep");
      assert.ok(edit.record.title && edit.record.body);
      assert.ok(Array.isArray(edit.record.sources) && edit.record.sources.length >= 2);
      assert.ok(edit.stagedArtifact.includes(edit.record.id));
    }
  });

  it("production without annotation finals fails closed (invents nothing)", async () => {
    const home = homeWithTranscripts(2);
    const stateDir = tmpDir();
    const proposal = await runPipeline({
      home,
      stateDir,
      analyzer: "acpx",
      runId: "run-PIPE-CLOSED",
      analyzeInvoke: () => ({ status: "ok", evidence: gapEvidence() }),
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
      synthesizeInvoke: ({ ledger }) => ({ status: "ok", result: { plans: [planForLedger(ledger)] } }),
      annotateInvoke: (args) => {
        if (args?.stage === "annotate-preface") return { status: "ok", ready: true };
        return { status: "ok", annotations: [] };
      },
    });
    assert.deepEqual(proposal.edits, []);
    assert.ok(proposal.staging.failed);
  });

  it("production synthesis failure yields no edits plus a visible proposal note", async () => {
    const home = homeWithTranscripts(2);
    const stateDir = tmpDir();
    const proposal = await runPipeline({
      home,
      stateDir,
      analyzer: "acpx",
      runId: "run-PIPE2",
      analyzeInvoke: () => ({ status: "ok", evidence: gapEvidence() }),
      consolidateInvoke: () => ({ status: "failed", error: "boom-consolidate" }),
      synthesizeInvoke: () => ({ status: "failed", error: "boom-synth" }),
    });
    assert.deepEqual(proposal.edits, []);
    assert.equal(proposal.synthesis.failed, true);
    assert.ok(typeof proposal.synthesis.note === "string" && proposal.synthesis.note.length > 0);
    assert.ok(proposal.notes.some((n) => /boom-synth|fail/i.test(n)));
  });

  it("prompt persistence failure surfaces a visible proposal/run note", async () => {
    const blocker = path.join(tmpDir(), "blocker");
    fs.writeFileSync(blocker, "x", "utf8");
    const badState = path.join(blocker, "nope");
    const ledger = {
      version: 1,
      minGapEvidence: 2,
      clusters: [
        {
          id: "g-a",
          proposedInstruction: "Bootstrap context once",
          representativeQuote: GAP_QUOTE,
          mistake: "m",
          sources: ["s1", "s2"],
          count: 2,
          eligible: true,
          perSource: { s1: { quote: GAP_QUOTE, mistake: "m" }, s2: { quote: GAP_QUOTE, mistake: "m" } },
        },
        {
          id: "g-b",
          proposedInstruction: "Do another thing",
          representativeQuote: GAP_QUOTE,
          mistake: "m",
          sources: ["s1", "s2"],
          count: 2,
          eligible: true,
          perSource: { s1: { quote: GAP_QUOTE, mistake: "m" }, s2: { quote: GAP_QUOTE, mistake: "m" } },
        },
      ],
    };
    const synth = synthesizeWithAcpx(ledger, {
      evidenceIndex: new Map(),
      invoke: ({ ledger: led }) => ({ status: "ok", plans: [planForLedger(led)] }),
      stateDir: badState,
      runId: "run-PP1",
    });
    assert.equal(synth.edits.length, 1);
    assert.ok(/persistence failed/i.test(synth.note || ""));
    const cons = consolidateLedger(ledger, {
      invoke: () => ({ status: "ok", merges: [] }),
      stateDir: badState,
      runId: "run-PP2",
    });
    assert.ok(/persistence failed/i.test(cons.note || ""));
  });
});
