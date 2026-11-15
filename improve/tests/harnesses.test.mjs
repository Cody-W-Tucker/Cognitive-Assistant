import { describe, it } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";

import { cutoffMs, discoverTranscripts, isLangfuseRevision, observationsToEvents, readTranscript, transcriptRevision } from "../src/harnesses.js";
import { langfuseClient, langfuseConfig } from "../src/langfuse.js";
import { SELF_SESSION_SENTINEL } from "../src/sentinel.js";
import { writeJson } from "../src/state.js";
import { HOUR, fakeLangfuse, sessionObservations } from "./fake-langfuse.mjs";

const now = Date.parse("2026-11-14T12:00:00Z");
const ago = (hours) => now - hours * HOUR;

describe("discovery from Langfuse root observations", () => {
  it("groups roots into sessions per harness, with times and per-harness metadata", async () => {
    const lf = fakeLangfuse();
    lf.add("hermes", "h1", { start: ago(30), platform: "tui", turns: [{ user: "a", assistant: "b" }, { user: "c", assistant: "d" }] });
    lf.add("claude", "c1", { start: ago(20), cwd: "/work/repo" });
    lf.add("opencode", "o1", { start: ago(15) });
    const { transcripts, perHarness } = await discoverTranscripts({ client: lf.client, since: "all", now });
    assert.deepEqual(transcripts.map((t) => [t.harness, t.id]), [["claude", "c1"], ["hermes", "h1"], ["opencode", "o1"]]);
    const hermes = transcripts.find((t) => t.id === "h1");
    assert.deepEqual([hermes.startedAtMs, hermes.mtimeMs, hermes.source, hermes.cwd], [ago(30), ago(30) + 10 * 60_000 + 60_000, "tui", null]);
    assert.equal(transcripts.find((t) => t.id === "c1").cwd, "/work/repo");
    assert.equal(transcripts.find((t) => t.id === "o1").source, null);
    assert.deepEqual(perHarness.hermes, { scanned: 1, matched: 1, self: 0, open: 0 });
    assert.ok(lf.calls.every((q) => q.isRootObservation === "true" && /metadata/.test(q.fields)), "discovery pages roots only");
  });

  it("drops evaluator runs, Pi turns and roots without a session", async () => {
    const lf = fakeLangfuse();
    lf.add("claude", "pi-session", { start: ago(20), source: "pi" });
    lf.add("claude", "judge", { start: ago(20), environment: "langfuse-llm-as-a-judge" });
    lf.observations.push(...sessionObservations("hermes", null, { start: ago(20) }));
    const { transcripts } = await discoverTranscripts({ client: lf.client, since: "all", now });
    assert.deepEqual(transcripts, []);
  });

  it("rejects excluded and unknown harnesses by name", async () => {
    const lf = fakeLangfuse();
    await assert.rejects(discoverTranscripts({ client: lf.client, harnesses: ["pi"] }), /machine\/automation/);
    await assert.rejects(discoverTranscripts({ client: lf.client, harnesses: ["codex"] }), /not traced to Langfuse/);
    await assert.rejects(discoverTranscripts({ client: lf.client, harnesses: ["vim"] }), /unknown harness/);
  });

  it("--since asks Langfuse for roots started inside the window", async () => {
    const lf = fakeLangfuse();
    lf.add("hermes", "old", { start: ago(24 * 40) });
    lf.add("hermes", "recent", { start: ago(24 * 2) });
    const { transcripts } = await discoverTranscripts({ client: lf.client, since: "30d", harnesses: ["hermes"], now });
    assert.deepEqual(transcripts.map((t) => t.id), ["recent"]);
    assert.equal(lf.calls[0].fromStartTime, new Date(cutoffMs("30d", now)).toISOString());
  });

  it("builds a session straddling --since from its full roots", async () => {
    const lf = fakeLangfuse();
    lf.add("hermes", "s", { start: ago(24 * 40), turns: [{ user: "old ask", assistant: "old reply" }] });
    lf.add("hermes", "s", { start: ago(24 * 2), turns: [{ user: "new ask", assistant: "new reply" }] });
    const { transcripts } = await discoverTranscripts({ client: lf.client, since: "30d", harnesses: ["hermes"], now });
    assert.deepEqual(transcripts.map((t) => t.id), ["s"]);
    assert.equal(transcripts[0].startedAtMs, ago(24 * 40));
    assert.deepEqual(transcripts[0].revision, await transcriptRevision({ harness: "hermes", id: "s" }, { client: lf.client }));
  });

  it("takes the session directory from the first turn that carries it", async () => {
    const lf = fakeLangfuse();
    lf.add("claude", "s", { start: ago(30), cwd: "/work/repo", turns: [{ user: "a", assistant: "b" }, { user: "c", assistant: "d" }] });
    lf.observations.find((o) => o.isRootObservation).metadata = { source: "claude-code" };
    const { transcripts } = await discoverTranscripts({ client: lf.client, since: "all", now });
    assert.equal(transcripts[0].cwd, "/work/repo");
  });

  it("orders a turn's assistant text before the next turn's user text at a shared boundary", () => {
    const turn = (id, startTime, endTime, user, assistant) => ({
      id, sessionId: "s", type: "CHAIN", name: "Conversational Turn", isRootObservation: true, environment: "default",
      metadata: { source: "claude-code" }, startTime, endTime,
      input: JSON.stringify({ role: "user", content: user }), output: JSON.stringify({ role: "assistant", content: assistant }),
    });
    const events = observationsToEvents("claude", [
      turn("r1", "2026-11-01T00:00:00.000Z", "2026-11-01T00:01:00.000Z", "A", "B"),
      turn("r2", "2026-11-01T00:01:00.000Z", "2026-11-01T00:02:00.000Z", "C", "D"),
    ]);
    assert.deepEqual(events.map((e) => e.text), ["A", "B", "C", "D"]);
  });

  it("skips a still-open session straddling --since without refetching its roots", async () => {
    const lf = fakeLangfuse();
    lf.add("hermes", "s", { start: ago(24 * 40), turns: [{ user: "old ask", assistant: "old reply" }] });
    lf.add("hermes", "s", { start: ago(1), turns: [{ user: "new ask", assistant: "new reply" }] });
    const { transcripts, perHarness } = await discoverTranscripts({ client: lf.client, since: "30d", harnesses: ["hermes"], now });
    assert.deepEqual(transcripts, []);
    assert.equal(perHarness.hermes.open, 1);
    assert.ok(lf.calls.every((q) => q.sessionId === undefined));
  });

  it("leaves sessions active within the idle window for later", async () => {
    const lf = fakeLangfuse();
    lf.add("claude", "busy", { start: ago(1) });
    lf.add("claude", "done", { start: ago(13) });
    const result = await discoverTranscripts({ client: lf.client, since: "all", now, idleHours: 12 });
    assert.deepEqual(result.transcripts.map((t) => t.id), ["done"]);
    assert.equal(result.perHarness.claude.open, 1);
    assert.equal((await discoverTranscripts({ client: lf.client, since: "all", now, idleHours: 0.5 })).transcripts.length, 2);
  });

  it("skips sessions the cursor holds at the same last activity, and re-finds those with a new turn", async (t) => {
    const lf = fakeLangfuse();
    lf.add("claude", "s", { start: ago(30) });
    const stateDir = (await import("./helpers.mjs")).tmpDir();
    const [session] = (await discoverTranscripts({ client: lf.client, stateDir, since: "all", now })).transcripts;
    writeJson(path.join(stateDir, "cursor.json"), { version: 2, processed: { "claude:s": session.mtimeMs } });
    assert.equal((await discoverTranscripts({ client: lf.client, stateDir, since: "all", now })).transcripts.length, 0);
    assert.equal((await discoverTranscripts({ client: lf.client, stateDir, since: "all", now, ignoreCheckpoint: true })).transcripts.length, 1);
    assert.equal((await discoverTranscripts({ client: lf.client, stateDir, since: "all", now, includeCheckpointed: () => true })).transcripts.length, 1);
    lf.add("claude", "s", { start: ago(20) });
    assert.equal((await discoverTranscripts({ client: lf.client, stateDir, since: "all", now })).transcripts.length, 1);
  });

  it("sessions rooted in the state dir are the runtime's own", async () => {
    const lf = fakeLangfuse();
    lf.add("claude", "mine", { start: ago(20), cwd: "/state/dir/run" });
    const result = await discoverTranscripts({ client: lf.client, stateDir: "/state/dir", since: "all", now });
    assert.deepEqual([result.transcripts.length, result.perHarness.claude.self], [0, 1]);
  });

  it("parses --since windows", () => {
    assert.equal(cutoffMs("all", now), 0);
    assert.equal(cutoffMs("2d", now), now - 2 * 86400_000);
    assert.equal(cutoffMs("1w", now), now - 7 * 86400_000);
    assert.throws(() => cutoffMs("yesterday", now), /--since/);
  });
});

describe("reading one session", () => {
  const tools = [["terminal", { command: "ls /etc/nixos" }, "flake.nix"], ["read_file", { path: "/etc/nixos/flake.nix" }, "{ inputs }"]];

  for (const harness of ["hermes", "claude", "opencode"]) {
    it(`normalizes ${harness} turns and tool calls into ordered events`, async () => {
      const lf = fakeLangfuse();
      lf.add(harness, "s", { start: ago(30), turns: [{ user: "first ask", assistant: "first reply", tools }, { user: "second ask", assistant: "second reply" }] });
      const { events, revision, self } = await readTranscript({ harness, id: "s" }, { client: lf.client });
      assert.equal(self, false);
      assert.deepEqual(events, [
        { kind: "message", role: "user", text: "first ask" },
        { kind: "tool", name: "terminal", input: { command: "ls /etc/nixos" }, result: "flake.nix" },
        { kind: "tool", name: "read_file", input: { path: "/etc/nixos/flake.nix" }, result: "{ inputs }" },
        { kind: "message", role: "assistant", text: "first reply" },
        { kind: "message", role: "user", text: "second ask" },
        { kind: "message", role: "assistant", text: "second reply" },
      ]);
      assert.ok(isLangfuseRevision(revision));
      assert.deepEqual(await transcriptRevision({ harness, id: "s" }, { client: lf.client }), revision);
    });
  }

  it("a Hermes turn that ended on tool calls has no assistant text", async () => {
    const lf = fakeLangfuse();
    lf.add("hermes", "s", { start: ago(30) });
    lf.observations.find((o) => o.isRootObservation).output = JSON.stringify({ content: null, tool_calls: [{ name: "x" }] });
    const { events } = await readTranscript({ harness: "hermes", id: "s" }, { client: lf.client });
    assert.ok(!events.some((e) => e.kind === "message" && e.role === "assistant"));
  });

  it("the revision changes with a new turn or a late end time, not with other sessions", async () => {
    const lf = fakeLangfuse();
    lf.add("claude", "s", { start: ago(30) });
    const session = { harness: "claude", id: "s" };
    const before = await transcriptRevision(session, { client: lf.client });
    lf.add("claude", "other", { start: ago(30) });
    assert.deepEqual(await transcriptRevision(session, { client: lf.client }), before);
    lf.observations.find((o) => o.sessionId === "s" && o.isRootObservation).endTime = new Date(ago(1)).toISOString();
    const late = await transcriptRevision(session, { client: lf.client });
    assert.notDeepEqual(late, before);
    lf.add("claude", "s", { start: ago(2) });
    assert.notDeepEqual(await transcriptRevision(session, { client: lf.client }), late);
    assert.equal(await transcriptRevision({ harness: "claude", id: "missing" }, { client: lf.client }), null);
  });

  it("recognizes the runtime's own session from its first user message", async () => {
    const lf = fakeLangfuse();
    lf.add("opencode", "s", { start: ago(30), turns: [{ user: `${SELF_SESSION_SENTINEL}\nprompt`, assistant: "ok" }] });
    assert.equal((await readTranscript({ harness: "opencode", id: "s" }, { client: lf.client })).self, true);
  });

  it("a session Langfuse does not hold is an error, not an empty transcript", async () => {
    await assert.rejects(readTranscript({ harness: "claude", id: "nope" }, { client: fakeLangfuse().client }), /not found in Langfuse/);
  });
});

describe("Langfuse client", () => {
  it("follows cursor pages", async () => {
    const lf = fakeLangfuse([], { pageSize: 2 });
    for (let i = 0; i < 5; i += 1) lf.add("claude", `s${i}`, { start: ago(30) });
    assert.equal((await lf.client.observations({ isRootObservation: true })).length, 5);
    assert.equal(lf.calls.length, 3);
  });

  it("retries 429 and 5xx, and fails on other errors", async () => {
    const lf = fakeLangfuse();
    lf.add("claude", "s", { start: ago(30) });
    lf.failNext(429, 503);
    assert.equal((await lf.client.observations({ isRootObservation: true })).length, 1);
    lf.failNext(403);
    await assert.rejects(lf.client.observations({}), /returned 403/);
    lf.failNext(500, 500, 500, 500, 500);
    await assert.rejects(lf.client.observations({}), /returned 500/);
  });

  it("reports an unreachable server", async () => {
    const client = langfuseClient({ baseUrl: "http://x", publicKey: "p", secretKey: "s", retryDelayMs: 1, fetch: async () => { throw new Error("ECONNREFUSED"); } });
    await assert.rejects(client.observations({}), /Langfuse unreachable at http:\/\/x: ECONNREFUSED/);
  });

  it("needs all three variables", () => {
    assert.throws(() => langfuseConfig({ LANGFUSE_PUBLIC_KEY: "p" }), /LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL not set/);
    assert.deepEqual(langfuseConfig({ LANGFUSE_PUBLIC_KEY: "p", LANGFUSE_SECRET_KEY: "s", LANGFUSE_BASE_URL: "u" }), { baseUrl: "u", publicKey: "p", secretKey: "s" });
  });
});
