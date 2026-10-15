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
    const tools = ["read", "search", "test"].map((name) => JSON.stringify({ kind: "tool", name, input: { name } }));
    fs.writeFileSync(path.join(dir, `2026-01-0${i + 1}T00-00-00Z.jsonl`), `${[payload, ...tools].join("\n")}\n`, "utf8");
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
  it("counts successful evidence from earlier checkpointed runs toward recurrence", async () => {
    const home = homeWithTranscripts(1);
    const stateDir = tmpDir();
    const options = {
      home,
      stateDir,
      analyzer: "mock",
      analyzeInvoke: () => ({ status: "ok", evidence: gapEvidence() }),
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
    };

    const first = await runPipeline(options);
    assert.equal(first.stats.eligible, 0, "one session alone cannot satisfy the recurrence floor");

    const sessions = path.join(home, ".codex", "sessions");
    fs.writeFileSync(
      path.join(sessions, "2026-01-02T00-00-00Z.jsonl"),
      `${[
        JSON.stringify({ role: "user", text: "same gap in a later session" }),
        ...["read", "search", "test"].map((name) => JSON.stringify({ kind: "tool", name })),
      ].join("\n")}\n`,
      "utf8",
    );
    const second = await runPipeline(options);
    assert.ok(second.stats.eligible >= 1, "prior successful evidence combines with the new session");
    assert.ok(second.edits.length >= 1, "eligible recurrence reaches the proposal path");
  });

  it("keeps successful session checkpoints across runs and analyzes only a newly discovered session", async () => {
    const home = homeWithTranscripts(2);
    const stateDir = tmpDir();
    let analysisCalls = 0;
    const analyzeInvoke = () => {
      analysisCalls += 1;
      return { status: "ok", evidence: gapEvidence() };
    };
    const options = {
      home,
      stateDir,
      analyzer: "mock",
      analyzeInvoke,
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
    };

    await runPipeline(options);
    assert.equal(analysisCalls, 2, "first run analyzes both discovered sessions");

    await runPipeline(options);
    assert.equal(analysisCalls, 2, "second run does not reanalyze successful sessions");

    const sessions = path.join(home, ".codex", "sessions");
    fs.writeFileSync(
      path.join(sessions, "2026-01-03T00-00-00Z.jsonl"),
      `${[
        JSON.stringify({ role: "user", text: "new session after checkpoint" }),
        ...["read", "search", "test"].map((name) => JSON.stringify({ kind: "tool", name })),
      ].join("\n")}\n`,
      "utf8",
    );
    await runPipeline(options);
    assert.equal(analysisCalls, 3, "the checkpoint retains prior sessions and admits only the new one");
  });

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
      synthesizeInvoke: (args) => {
        const ledger = args?.ledger;
        const plans = [planForLedger(ledger)];
        // TEXT-ONLY: return stdout plans only with no filesystem access;
        // deterministic code materializes under synthesis-workspace.
        assert.equal(args?.cwd, undefined, "text-only invoke must not receive cwd");
        assert.equal(args?.workspace, undefined, "text-only invoke must not receive workspace");
        return { status: "ok", result: { plans } };
      },
      annotateInvoke: (args) => {
        if (args?.stage === "annotate-preface") return { status: "ok", ready: true };
        const plans = args?.staged || [];
        // Production invoke supplies complete finals; the test double builds
        // them from the staged plans without inventing sessions.
        // (production success path — runs once)
        return {
          status: "ok",
          annotations: plans.map((p, i) => ({
            id: p.id || `e${i + 1}`,
            verdict: "keep",
            reason: String(p.provisionalIntent || "keep"),
            record: {
              id: `exp-test-a1b2c3d4e5f${i}`,
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
    assert.ok(proposal.synthesis.failed || proposal.staging.failed, "fail-closed must be visible via synthesis or staging");
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
    // EDIT-ONLY: JSON plans alone never yield durable edits; with an
    // unwritable stateDir (no observable workspace) synthesis fails closed.
    const synth = synthesizeWithAcpx(ledger, {
      evidenceIndex: new Map(),
      invoke: ({ ledger: led }) => ({ status: "ok", plans: [planForLedger(led)] }),
      stateDir: badState,
      runId: "run-PP1",
    });
    assert.deepEqual(synth.edits, []);
    assert.ok(/fail-closed|no workspace/i.test(synth.note || ""));
    const cons = consolidateLedger(ledger, {
      invoke: () => ({ status: "ok", merges: [] }),
      stateDir: badState,
      runId: "run-PP2",
    });
    assert.ok(/persistence failed/i.test(cons.note || ""));
  });

  it("deterministic code materializes validated text-only plans: pipeline never fabricates seed edits", async () => {
    const home = homeWithTranscripts(2);
    const stateDir = tmpDir();
    const proposal = await runPipeline({
      home,
      stateDir,
      analyzer: "acpx",
      runId: "run-NOFAB1",
      analyzeInvoke: () => ({ status: "ok", evidence: gapEvidence() }),
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
      // TEXT-ONLY: injected production synthesis returns stdout plans with no
      // filesystem access; deterministic code materializes validated plans.
      synthesizeInvoke: ({ ledger }) => ({ status: "ok", result: { plans: [planForLedger(ledger)] } }),
      annotateInvoke: (args) => {
        if (args?.stage === "annotate-preface") return { status: "ok", ready: true };
        const plans = args?.staged || [];
        return {
          status: "ok",
          annotations: plans.map((p, i) => ({
            id: p.id || `e${i + 1}`,
            verdict: "keep",
            reason: String(p.provisionalIntent || "keep"),
            record: {
              id: `exp-test-a1b2c3d4e5f${i}`,
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
    assert.ok(proposal.edits.length >= 1, "validated text-only plans materialize to candidate edits");
    const measured = JSON.parse(fs.readFileSync(path.join(stateDir, "measured-changes.json"), "utf8"));
    const changes = measured.changes || measured;
    assert.ok(changes.length >= 1, "pipeline measures deterministically materialized workspace changes");
    assert.ok(fs.existsSync(path.join(stateDir, "synthesis-workspace", "e1.md")));
    assert.ok(!fs.existsSync(path.join(stateDir, "synthesis-workspace", "seed-keep.md")), "synthetic seed records do not exist");
    assert.ok(!fs.existsSync(path.join(stateDir, "synthesis-workspace", "seed-remove.md")), "synthetic seed records do not exist");
  });

  it("traces with no actual analyzer gap evidence never create synthetic gaps (RED)", async () => {
    const home = homeWithTranscripts(2);
    const stateDir = tmpDir();
    const proposal = await runPipeline({
      home,
      stateDir,
      analyzer: "mock",
      runId: "run-NOSYNTH",
      analyzeInvoke: () => ({ status: "ok", evidence: { status: "ok", positive: [], negative: [], gaps: [] } }),
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
    });
    assert.deepEqual(proposal.edits, []);
    assert.equal(proposal.stats.clusters, 0, "no analyzer gaps means no clusters");
    assert.equal(proposal.stats.eligible, 0);
    const ledger = JSON.parse(fs.readFileSync(path.join(stateDir, "ledger.json"), "utf8"));
    assert.deepEqual(ledger.clusters, [], "ledger must not fabricate fallback gaps from distilled traces");
    let gaps = null;
    try {
      gaps = JSON.parse(fs.readFileSync(path.join(stateDir, "open-gaps.json"), "utf8")).gaps;
    } catch {
      gaps = [];
    }
    assert.deepEqual(gaps, [], "open-gap ledger must only persist actual analyzer gap observations");
  });

  it("mock synthesis authors the workspace and each final binds its specific change", async () => {
    const home = homeWithTranscripts(2);
    const stateDir = tmpDir();
    const proposal = await runPipeline({
      home,
      stateDir,
      analyzer: "mock",
      runId: "run-MOCKBIND1",
      analyzeInvoke: () => ({ status: "ok", evidence: gapEvidence() }),
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
    });
    assert.ok(proposal.edits.length >= 1);
    const measured = JSON.parse(fs.readFileSync(path.join(stateDir, "measured-changes.json"), "utf8"));
    const changes = measured.changes || measured;
    const byId = new Map(changes.map((m) => [String(m.id), m]));
    for (const edit of proposal.edits) {
      assert.ok(edit.measuredIds && edit.measuredIds.length >= 1, "each final binds specific measured IDs");
      for (const mid of edit.measuredIds) assert.ok(byId.has(String(mid)), `measured ID ${mid} resolves`);
      // No blanket attachment: the edit's IDs must be a strict subset scoped
      // to its own plan file, never the full workspace change set.
      assert.ok(edit.measuredIds.length < changes.length || changes.length === 1, "binding must be specific, not blanket all-IDs");
    }
  });
});
