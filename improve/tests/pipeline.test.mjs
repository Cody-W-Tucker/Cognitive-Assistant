import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import { runPipeline } from "../src/pipeline.js";
import { readJson } from "../src/state.js";
import { invokeWith, tmpDir, writeCodexSession, writeSoul } from "./helpers.mjs";

/** A HOME with `n` substantial Codex sessions plus a fresh state dir and SOUL. */
function setup(n = 2) {
  const root = tmpDir();
  const home = path.join(root, "home");
  for (let i = 0; i < n; i += 1) writeCodexSession(home, `codex-${i}`);
  return { home, stateDir: path.join(root, "state"), soulPath: writeSoul(root) };
}

const run = (env, options = {}) => runPipeline({ ...env, since: "all", analyzer: "mock", ...options });

describe("run with the mock analyzer", () => {
  it("proposes one complete, validated record from a gap recurring in two sessions", async () => {
    const env = setup(2);
    const invoke = invokeWith();
    const proposal = await run(env, { invoke });
    assert.equal(proposal.edits.length, 1);
    const [edit] = proposal.edits;
    assert.equal(edit.annotation.verdict, "keep");
    assert.match(edit.record.id, /^exp-[a-z0-9-]+-[0-9a-f]{12}$/);
    assert.deepEqual(edit.record.sources, ["codex-0", "codex-1"]);
    assert.deepEqual(edit.evidence, edit.record.evidence);
    assert.equal(edit.title, `Experience record: ${edit.record.title}`);
    assert.deepEqual(proposal.stats, { transcripts: 2, analyzed: 2, skipped: 0, failed: 0, clusters: 1, eligible: 1 });
    assert.equal(proposal.appliedAt, null);
    assert.equal(proposal.soul.path, env.soulPath);
    assert.deepEqual(readJson(path.join(env.stateDir, "proposal.json")), proposal);
    assert.deepEqual(invoke.calls.map((c) => c.role), ["analysis", "analysis", "synthesis", "annotate"]);
    for (const name of ["ledger.json", "open-gaps.json", "cursor.json", "evidence/codex-0.json"]) {
      assert.ok(fs.existsSync(path.join(env.stateDir, name)), name);
    }
  });

  it("checkpoints sessions: a second run analyzes only what is new, yet earlier evidence still counts", async () => {
    const env = setup(1);
    const invoke = invokeWith();
    const first = await run(env, { invoke });
    assert.equal(first.stats.eligible, 0, "one session cannot meet the evidence floor");
    assert.equal(first.edits.length, 0);
    await run(env, { invoke });
    assert.equal(invoke.calls.filter((c) => c.role === "analysis").length, 1, "an unchanged session is not re-analyzed");
    writeCodexSession(env.home, "codex-later", { day: "13" });
    const third = await run(env, { invoke });
    assert.equal(invoke.calls.filter((c) => c.role === "analysis").length, 2);
    assert.equal(third.stats.transcripts, 1);
    assert.equal(third.edits.length, 1, "the new session plus saved evidence reach the floor");
  });

  it("evidence carries session time, and a failed re-analysis keeps the earlier good evidence", async () => {
    const env = setup(1);
    const file = path.join(env.home, ".codex", "sessions", "2026", "10", "12", "rollout-codex-0.jsonl");
    await run(env);
    const evidenceFile = path.join(env.stateDir, "evidence", "codex-0.json");
    assert.equal(typeof readJson(evidenceFile).sessionAt, "number");
    fs.appendFileSync(file, `${JSON.stringify({ role: "user", content: "one more thing" })}\n`);
    const later = new Date(Date.now() + 5000);
    fs.utimesSync(file, later, later);
    const failing = invokeWith({
      analysis: () => {
        throw new Error("timed out");
      },
    });
    const proposal = await run(env, { invoke: failing });
    assert.equal(proposal.stats.failed, 1);
    assert.equal(readJson(evidenceFile).status, "ok");
  });

  it("sessions without analyzer gaps never produce a cluster", async () => {
    const env = setup(2);
    const proposal = await run(env, { invoke: invokeWith({ analysis: () => ({ positive: [], negative: [], gaps: [] }) }) });
    assert.deepEqual([proposal.stats.clusters, proposal.edits.length], [0, 0]);
  });

  it("a synthesis failure or invalid plans yield no edits and a visible note", async () => {
    for (const synthesis of [
      () => {
        throw new Error("endpoint down");
      },
      () => ({ plans: [{ clusterId: "g-unknown", provisionalIntent: "x", provisionalSources: ["a", "b"] }] }),
    ]) {
      const invoke = invokeWith({ synthesis });
      const proposal = await run(setup(2), { invoke });
      assert.deepEqual(proposal.edits, []);
      assert.equal(proposal.synthesis.failed, true);
      assert.match(proposal.notes.join("\n"), /synthesis (failed|plans invalid)/);
      assert.ok(!invoke.calls.some((c) => c.role === "annotate"), "nothing to annotate");
    }
  });

  it("an annotation that is missing or carries a paraphrased quote yields no edits", async () => {
    for (const annotate of [() => ({ annotations: [] }), (ctx) => paraphrased(ctx)]) {
      const proposal = await run(setup(2), { invoke: invokeWith({ annotate }) });
      assert.deepEqual(proposal.edits, []);
      assert.equal(proposal.annotation.failed, true);
      assert.match(proposal.notes.join("\n"), /annotate failed/);
    }
  });

  it("a rejected identity stays suppressed until new evidence arrives", async () => {
    const env = setup(2);
    const first = await run(env);
    const { record } = first.edits[0];
    const row = { proposal: first.id, edit: "e1", reason: "too-narrow", title: record.title, clusterId: record.clusterId, recordId: record.id, sources: record.sources };
    fs.writeFileSync(path.join(env.stateDir, "rejections.jsonl"), `${JSON.stringify(row)}\n`);
    const invoke = invokeWith();
    const second = await run(env, { invoke });
    assert.deepEqual(second.edits, []);
    assert.ok(invoke.calls.find((c) => c.role === "synthesis").prompt.includes(`[e1] ${record.title}`), "rejections reach the synthesis prompt");
    writeCodexSession(env.home, "codex-new", { day: "14" });
    const third = await run(env);
    assert.equal(third.edits.length, 1, "a session the rejection did not cite lifts suppression");
  });

  it("a gap corroborated from an earlier run is marked on the edit", async () => {
    const env = setup(1);
    await run(env);
    writeCodexSession(env.home, "codex-b", { day: "13" });
    fs.rmSync(path.join(env.stateDir, "evidence", "codex-0.json"));
    const proposal = await run(env);
    assert.equal(proposal.edits.length, 1);
    assert.equal(proposal.edits[0].corroboratedOpenGap, true);
    assert.match(proposal.edits[0].rationale, /^open-gap corroborated singleton: /);
    assert.deepEqual(proposal.edits[0].record.sources, ["codex-0", "codex-b"]);
  });

  it("fails before any work when the SOUL is missing or empty, or the analyzer is unknown", async () => {
    const env = setup(2);
    await assert.rejects(run({ ...env, soulPath: path.join(env.stateDir, "nope.md") }), /SOUL baseline unavailable/);
    fs.writeFileSync(env.soulPath, "  \n");
    await assert.rejects(run(env), /SOUL baseline .* is empty/);
    assert.equal(fs.existsSync(env.stateDir), false);
    await assert.rejects(run(setup(1), { analyzer: "llm" }), /--analyzer must be model or mock/);
  });

  it("a real run without a configured endpoint fails before analyzing anything", async () => {
    const env = setup(2);
    const saved = process.env.CA_LLM_BASE_URL;
    delete process.env.CA_LLM_BASE_URL;
    try {
      await assert.rejects(run(env, { analyzer: "model" }), /CA_LLM_BASE_URL is not set/);
    } finally {
      if (saved !== undefined) process.env.CA_LLM_BASE_URL = saved;
    }
    assert.equal(fs.existsSync(path.join(env.stateDir, "evidence")), false);
  });
});

/** The mock annotation with one quote reworded, which validation must refuse. */
async function paraphrased(context) {
  const { mockInvoke } = await import("../src/mock.js");
  const reply = await mockInvoke("annotate", "", context);
  reply.annotations[0].record.evidence[0].text += " (paraphrased)";
  return reply;
}
