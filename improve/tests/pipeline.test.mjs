import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import { sessionMeta } from "../src/outcome.js";
import { capSessions, runPipeline } from "../src/pipeline.js";
import { SELF_SESSION_SENTINEL } from "../src/sentinel.js";
import { readJson } from "../src/state.js";
import { HOUR } from "./fake-langfuse.mjs";
import { invokeWith, setup } from "./helpers.mjs";

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
    assert.deepEqual(edit.record.sources, ["claude-0", "claude-1"]);
    assert.deepEqual(edit.evidence, edit.record.evidence);
    assert.equal(edit.title, `Experience record: ${edit.record.title}`);
    assert.deepEqual(proposal.stats, { transcripts: 2, analyzed: 2, skipped: 0, failed: 0, clusters: 1, eligible: 1 });
    assert.equal(proposal.appliedAt, null);
    assert.equal(proposal.soul.path, env.soulPath);
    assert.deepEqual(readJson(path.join(env.stateDir, "proposal.json")), proposal);
    assert.deepEqual(invoke.calls.map((c) => c.role), ["analysis", "analysis", "synthesis", "annotate"]);
    for (const name of ["ledger.json", "open-gaps.json", "cursor.json", "evidence/claude:claude-0.json"]) {
      assert.ok(fs.existsSync(path.join(env.stateDir, name)), name);
    }
    const snapshot = readJson(path.join(env.stateDir, "evidence", "claude:claude-0.json")).outcomeSnapshot;
    assert.deepEqual(snapshot.location, { harness: "claude", id: "claude-0" });
    assert.equal(snapshot.revision.source, "langfuse");
    assert.match(snapshot.trace, /source: langfuse session claude-0/);
  });

  it("checkpoints sessions: a second run analyzes only what is new, yet earlier evidence still counts", async () => {
    const env = setup(1);
    const invoke = invokeWith();
    const first = await run(env, { invoke });
    assert.equal(first.stats.eligible, 0, "one session cannot meet the evidence floor");
    assert.equal(first.edits.length, 0);
    await run(env, { invoke });
    assert.equal(invoke.calls.filter((c) => c.role === "analysis").length, 1, "an unchanged session is not re-analyzed");
    env.langfuse.add("claude", "claude-later");
    const third = await run(env, { invoke });
    assert.equal(invoke.calls.filter((c) => c.role === "analysis").length, 2);
    assert.equal(third.stats.transcripts, 1);
    assert.equal(third.edits.length, 1, "the new session plus saved evidence reach the floor");
  });

  it("evidence carries session time and rubric, and is never re-analyzed after a new turn", async () => {
    const env = setup(1);
    await run(env);
    const evidenceFile = path.join(env.stateDir, "evidence", "claude:claude-0.json");
    const evidence = readJson(evidenceFile);
    assert.equal(typeof evidence.sessionAt, "number");
    assert.match(evidence.rubric.promptSha, /^[a-f0-9]{64}$/);
    assert.match(evidence.rubric.contextSha, /^[a-f0-9]{64}$/);
    assert.equal(evidence.rubric.model, "mock");
    env.langfuse.add("claude", "claude-0", { start: Date.now() - 24 * HOUR, turns: [{ user: "one more thing", assistant: "ok" }] });
    const failing = invokeWith({ analysis: () => { throw new Error("timed out"); } });
    const proposal = await run(env, { invoke: failing });
    assert.equal(proposal.stats.transcripts, 0);
    assert.deepEqual(readJson(evidenceFile), evidence);
    const cursor = readJson(path.join(env.stateDir, "cursor.json"));
    assert.ok(cursor.processed["claude:claude-0"] > evidence.sessionAt, "the session is re-checkpointed at its new activity");
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
    env.langfuse.add("claude", "claude-new");
    const third = await run(env);
    assert.equal(third.edits.length, 1, "a session the rejection did not cite lifts suppression");
  });

  it("a gap corroborated from an earlier run is marked on the edit", async () => {
    const env = setup(1);
    await run(env);
    env.langfuse.add("claude", "claude-b");
    fs.rmSync(path.join(env.stateDir, "evidence", "claude:claude-0.json"));
    const proposal = await run(env);
    assert.equal(proposal.edits.length, 1);
    assert.equal(proposal.edits[0].corroboratedOpenGap, true);
    assert.match(proposal.edits[0].rationale, /^open-gap corroborated singleton: /);
    assert.deepEqual(proposal.edits[0].record.sources, ["claude-0", "claude-b"]);
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

  it("fails loudly when Langfuse is unconfigured or refuses, rather than finding no sessions", async () => {
    const env = setup(2);
    const saved = { ...process.env };
    for (const name of ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"]) delete process.env[name];
    try {
      await assert.rejects(run({ ...env, client: null }), /LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL not set/);
    } finally {
      Object.assign(process.env, saved);
    }
    env.langfuse.failNext(401);
    await assert.rejects(run(env), /Langfuse .* returned 401/);
    assert.equal(fs.existsSync(path.join(env.stateDir, "proposal.json")), false);
  });

  it("skips and checkpoints the runtime's own sessions", async () => {
    const env = setup(0);
    env.langfuse.add("claude", "self-prompt", { turns: [{ user: `${SELF_SESSION_SENTINEL}\nanalyze this`, assistant: "ok", tools: [["a", {}, ""], ["b", {}, ""], ["c", {}, ""]] }] });
    env.langfuse.add("claude", "self-cwd", { cwd: path.join(env.stateDir, "work") });
    const invoke = invokeWith();
    const proposal = await run(env, { invoke });
    assert.deepEqual([proposal.stats.transcripts, proposal.stats.skipped], [1, 1]);
    assert.equal(invoke.calls.filter((c) => c.role === "analysis").length, 0);
    assert.deepEqual(Object.keys(readJson(path.join(env.stateDir, "cursor.json")).processed), ["claude:self-prompt"]);
  });
});

it("uses start and metadata with safe fallbacks", () => {
  const session = { startedAtMs: 100, mtimeMs: 200, source: "cli", cwd: "/a" };
  assert.deepEqual(sessionMeta(session), { sessionAt: 100, startedAt: 100, endedAt: "1970-01-01T00:00:00.200Z", source: "cli", cwd: "/a", gitRepoRoot: null, parentSessionId: null });
  assert.equal(sessionMeta({ harness: "hermes", mtimeMs: 200 }).endedAt, "1970-01-01T00:00:00.200Z");
  assert.equal(sessionMeta({ mtimeMs: 200 }).sessionAt, 200);
  assert.equal(sessionMeta({}).startedAt, null);
  assert.equal(sessionMeta({}).endedAt, null);
  assert.equal(sessionMeta({ harness: "hermes", mtimeMs: 200 }).sessionAt, null);
});

it("gates every harness on idle time and leaves open sessions off the cursor", async () => {
  const now = Date.now();
  const env = setup(0);
  env.langfuse.add("hermes", "open", { start: now - 5 * 60_000 });
  env.langfuse.add("opencode", "open-oc", { start: now - 5 * 60_000 });
  const proposal = await run(env);
  assert.equal(proposal.stats.transcripts, 0);
  assert.deepEqual(readJson(path.join(env.stateDir, "cursor.json")).processed, {});
});

/** The mock annotation with one quote reworded, which validation must refuse. */
async function paraphrased(context) {
  const { mockInvoke } = await import("../src/mock.js");
  const reply = await mockInvoke("annotate", "", context);
  reply.annotations[0].record.evidence[0].text += " (paraphrased)";
  return reply;
}

it("repairs checkpointed legacy Hermes metadata without re-analysis or inventing a rubric", async () => {
  const env = setup(0);
  const start = Date.now() - 30 * HOUR;
  env.langfuse.add("hermes", "old", { start, platform: "cli" });
  env.langfuse.add("hermes", "unknown-source", { start, platform: null });
  fs.mkdirSync(path.join(env.stateDir, "evidence"), { recursive: true });
  for (const id of ["old", "unknown-source"]) {
    fs.writeFileSync(path.join(env.stateDir, "evidence", `${id}.json`), JSON.stringify({ harness: "hermes", transcriptId: id, status: "ok", negative: [{ quote: "original" }], gaps: [], sessionAt: 123 }));
  }
  fs.writeFileSync(path.join(env.stateDir, "cursor.json"), JSON.stringify({ version: 2, processed: { "hermes:old": 1, "hermes:unknown-source": 1 } }));
  const invoke = invokeWith();
  const result = await run(env, { harnesses: ["hermes"], invoke });
  assert.equal(result.stats.transcripts, 0);
  assert.equal(invoke.calls.filter((c) => c.role === "analysis").length, 0);
  const repaired = readJson(path.join(env.stateDir, "evidence", "hermes:old.json"));
  assert.equal(repaired.sessionAt, start);
  assert.equal(repaired.source, "cli");
  assert.equal(repaired.endedAt, new Date(start + 60_000).toISOString());
  assert.deepEqual(repaired.negative, [{ quote: "original" }]);
  assert.equal(repaired.rubric, undefined);
  assert.equal(fs.existsSync(path.join(env.stateDir, "evidence", "hermes:unknown-source.json")), false);
});

it("passes the configured idle window into discovery", async () => {
  const env = setup(0);
  env.langfuse.add("hermes", "idle", { start: Date.now() - 2 * HOUR });
  const result = await run(env, { harnesses: ["hermes"], idleHours: 0.5 });
  assert.equal(result.stats.transcripts, 1);
});

it("capSessions keeps Hermes first, then the newest, and leaves an uncapped list alone", () => {
  const rows = [
    { id: "c-old", harness: "claude", mtimeMs: 1 },
    { id: "c-new", harness: "claude", mtimeMs: 9 },
    { id: "h-old", harness: "hermes", mtimeMs: 2 },
  ];
  assert.deepEqual(capSessions(rows, 2).map((t) => t.id), ["h-old", "c-new"]);
  assert.equal(capSessions(rows, null), rows);
  assert.equal(capSessions(rows, 3), rows);
});

it("--max-sessions bounds a run; checkpoints let the next run take the rest", async () => {
  const env = setup(3);
  const invoke = invokeWith();
  const first = await run(env, { invoke, maxSessions: 2 });
  assert.equal(first.stats.transcripts, 2);
  const second = await run(env, { invoke, maxSessions: 2 });
  assert.equal(second.stats.transcripts, 1);
  assert.equal(invoke.calls.filter((c) => c.role === "analysis").length, 3);
  await assert.rejects(run(env, { maxSessions: 0 }), /--max-sessions must be a positive integer/);
});
