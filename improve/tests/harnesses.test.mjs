import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import { cutoffMs, discoverTranscripts, opencodeExportToEvents, readTranscriptEvents } from "../src/harnesses.js";
import { codex, daysAgoSec, makeSqlite, nowSec, tmpDir, writeCodexSession, writeJsonl } from "./helpers.mjs";

const OPENCODE_V2 = [
  ["CREATE TABLE session_v2 (id TEXT PRIMARY KEY, project_id TEXT, directory TEXT, title TEXT, time_created INTEGER, time_updated INTEGER)"],
  ["CREATE TABLE session_message (id TEXT PRIMARY KEY, session_id TEXT, type TEXT, seq INTEGER, time_created INTEGER, time_updated INTEGER, data TEXT)"],
];
const HERMES_SESSIONS = "CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT, source TEXT, created_at INTEGER, updated_at INTEGER)";
const HERMES_MESSAGES = "CREATE TABLE messages (id TEXT PRIMARY KEY, session_id TEXT, role TEXT, text BLOB)";

const opencodeDb = (home) => path.join(home, ".local", "share", "opencode", "opencode.db");
const hermesDb = (home) => path.join(home, ".hermes", "state.db");
const ids = (result) => result.transcripts.map((t) => t.id);

/** A fake HOME with one session per supported store plus excluded-store and self-session traps. */
function fixtureHome() {
  const root = tmpDir();
  const home = path.join(root, "fakehome");
  writeJsonl(path.join(home, ".claude", "projects", "-tmp-proj", "claude-1.jsonl"), [
    { cwd: "/tmp/proj", sessionId: "claude-1", type: "user", message: { content: "fix the bug" } },
    { cwd: "/tmp/proj", sessionId: "claude-1", type: "assistant", message: { content: "fixed" } },
  ]);
  writeJsonl(path.join(home, ".codex", "sessions", "2026", "10", "11", "rollout-001-codex-1.jsonl"), [
    codex.meta("codex-1"),
    codex.message("user", "add a test"),
  ]);
  writeJsonl(path.join(home, ".codex", "sessions", "2026", "10", "11", "rollout-002-self.jsonl"), [
    codex.meta("self-1"),
    codex.message("user", "<!-- ca-improve:self-session --> analyze this"),
  ]);
  const now = nowSec();
  makeSqlite(opencodeDb(home), [
    ...OPENCODE_V2,
    ["INSERT INTO session_v2 VALUES ('opencode-1', 'p1', '/tmp/proj', 't', ?, ?)", now, now],
    ["INSERT INTO session_message VALUES ('m1', 'opencode-1', 'user', 0, ?, ?, ?)", now, now, JSON.stringify({ role: "user", text: "review this diff" })],
  ]);
  makeSqlite(hermesDb(home), [
    [HERMES_SESSIONS],
    ["INSERT INTO sessions VALUES ('hermes-1', '/tmp/proj', 'cli', ?, ?)", now, now],
    [HERMES_MESSAGES],
    ["INSERT INTO messages VALUES ('hm1', 'hermes-1', 'user', 'check the logs')"],
  ]);
  writeJsonl(path.join(home, ".pi", "agent", "sessions", "-tmp-proj", "2026-10-11T00-00-00_pi-1.jsonl"), [
    { type: "session", cwd: "/tmp/proj", id: "pi-1" },
    { role: "user", content: "help me refactor this" },
  ]);
  writeJsonl(path.join(home, ".grok", "sessions", "grok-1.jsonl"), [{ role: "user", content: "grok session" }]);
  writeJsonl(path.join(home, ".cursor", "sessions", "cursor-1.jsonl"), [{ role: "user", content: "cursor session" }]);
  return { root, home, stateDir: path.join(root, "state") };
}

describe("discovery across harness stores", () => {
  it("finds all four supported stores under HOME regardless of cwd, and ignores excluded stores", () => {
    const { root, home, stateDir } = fixtureHome();
    const elsewhere = path.join(root, "elsewhere");
    fs.mkdirSync(elsewhere);
    const cwd = process.cwd();
    process.chdir(elsewhere);
    let result;
    try {
      result = discoverTranscripts({ home, stateDir });
    } finally {
      process.chdir(cwd);
    }
    assert.deepEqual(new Set(result.transcripts.map((t) => t.harness)), new Set(["claude", "codex", "opencode", "hermes"]));
    for (const id of ["pi-1", "grok-1", "cursor-1", "self-1"]) assert.ok(!ids(result).includes(id), `${id} must not be discovered`);
    for (const harness of ["pi", "grok", "cursor"]) assert.ok(harness in result.excluded);
    for (const t of result.transcripts) assert.ok((t.path || t.db).startsWith(home), `${t.id} is not under HOME`);
    assert.equal(result.perHarness.codex.self, 1);
  });

  it("rejects an explicitly named excluded harness", () => {
    const { home, stateDir } = fixtureHome();
    assert.throws(() => discoverTranscripts({ home, stateDir, harnesses: ["pi"] }), /machine\/automation/);
    assert.throws(() => discoverTranscripts({ home, stateDir, harnesses: ["vim"] }), /unknown harness/);
  });

  it("--since drops old timestamped OpenCode and Hermes rows", () => {
    const root = tmpDir();
    const home = path.join(root, "fakehome");
    const [old, now] = [daysAgoSec(90), nowSec()];
    makeSqlite(opencodeDb(home), [
      ...OPENCODE_V2,
      ["INSERT INTO session_v2 VALUES ('opencode-old', 'p1', '/tmp/proj', 'old', ?, ?)", old, old],
      ["INSERT INTO session_v2 VALUES ('opencode-new', 'p1', '/tmp/proj', 'new', ?, ?)", now, now],
    ]);
    makeSqlite(hermesDb(home), [
      [HERMES_SESSIONS],
      ["INSERT INTO sessions VALUES ('hermes-old', '/tmp/proj', 'cli', ?, ?)", old, old],
      ["INSERT INTO sessions VALUES ('hermes-new', '/tmp/proj', 'cli', ?, ?)", now, now],
    ]);
    const found = ids(discoverTranscripts({ home, stateDir: path.join(root, "state"), since: "30d" }));
    assert.deepEqual(found.sort(), ["hermes-new", "opencode-new"]);
  });

  it("skips a session the cursor already processed", () => {
    const root = tmpDir();
    const home = path.join(root, "fakehome");
    makeSqlite(hermesDb(home), [
      ["CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT)"],
      ["INSERT INTO sessions VALUES ('hermes-seen', '/tmp/proj')"],
      ["INSERT INTO sessions VALUES ('hermes-fresh', '/tmp/proj')"],
    ]);
    const stateDir = path.join(root, "state");
    fs.mkdirSync(stateDir);
    fs.writeFileSync(path.join(stateDir, "cursor.json"), JSON.stringify({ version: 2, processed: { "hermes:hermes-seen": null } }));
    assert.deepEqual(ids(discoverTranscripts({ home, stateDir, since: "30d" })), ["hermes-fresh"]);
  });

  it("re-discovers a timestamped session whose revision changed since the cursor", () => {
    const root = tmpDir();
    const home = path.join(root, "fakehome");
    const file = writeJsonl(path.join(home, ".codex", "sessions", "a.jsonl"), [{ id: "c1" }, { role: "user", content: "x" }]);
    const stateDir = path.join(root, "state");
    fs.mkdirSync(stateDir);
    const mtimeMs = Math.round(fs.statSync(file).mtimeMs);
    fs.writeFileSync(path.join(stateDir, "cursor.json"), JSON.stringify({ version: 2, processed: { "codex:c1": mtimeMs } }));
    assert.deepEqual(ids(discoverTranscripts({ home, stateDir, harnesses: ["codex"] })), []);
    fs.writeFileSync(path.join(stateDir, "cursor.json"), JSON.stringify({ version: 2, processed: { "codex:c1": mtimeMs - 1000 } }));
    assert.deepEqual(ids(discoverTranscripts({ home, stateDir, harnesses: ["codex"] })), ["c1"]);
  });

  it("sessions rooted in the state dir are the runtime's own", () => {
    const root = tmpDir();
    const home = path.join(root, "fakehome");
    const stateDir = path.join(root, "state");
    writeJsonl(path.join(home, ".codex", "sessions", "own.jsonl"), [{ id: "own", cwd: path.join(stateDir, "x") }]);
    const result = discoverTranscripts({ home, stateDir, harnesses: ["codex"] });
    assert.deepEqual(ids(result), []);
    assert.equal(result.perHarness.codex.self, 1);
  });

  it("a missing store is reported softly by default and fails when the harness is named", () => {
    const home = tmpDir();
    const stateDir = path.join(tmpDir(), "state");
    assert.throws(() => discoverTranscripts({ home, stateDir, harnesses: ["hermes"], strict: true }), /hermes: store missing/);
    assert.equal(discoverTranscripts({ home, stateDir, harnesses: ["hermes"] }).perHarness.hermes.error, "store missing");
  });

  it("keeps readable siblings when a JSONL descendant vanishes or is inaccessible", (t) => {
    const readdir = fs.readdirSync;
    for (const harness of ["claude", "codex"]) {
      for (const code of ["ENOENT", "EACCES"]) {
        const home = tmpDir();
        const root = path.join(home, `.${harness}`, harness === "claude" ? "projects" : "sessions");
        const bad = path.join(root, "bad");
        fs.mkdirSync(bad, { recursive: true });
        writeJsonl(path.join(root, "good", "session.jsonl"), [{ id: "readable" }]);
        const mock = t.mock.method(fs, "readdirSync", (dir, options) => {
          if (dir === bad) throw Object.assign(new Error(code), { code });
          return readdir(dir, options);
        });
        try {
          const found = discoverTranscripts({ home, harnesses: [harness], since: "all", strict: true });
          assert.deepEqual(ids(found), ["readable"]);
        } finally {
          mock.mock.restore();
        }
      }
    }
  });

  it("isolates configured Claude root failures but reports a wholly inaccessible store", (t) => {
    const home = tmpDir();
    const config = path.join(home, "config");
    const defaultRoot = path.join(home, ".claude", "projects");
    const configRoot = path.join(config, "projects");
    writeJsonl(path.join(defaultRoot, "default.jsonl"), [{ id: "default" }]);
    writeJsonl(path.join(configRoot, "config.jsonl"), [{ id: "config" }]);
    const oldHome = process.env.HOME;
    const oldConfig = process.env.CLAUDE_CONFIG_DIR;
    const stat = fs.statSync;
    const readdir = fs.readdirSync;
    process.env.HOME = home;
    process.env.CLAUDE_CONFIG_DIR = config;
    try {
      for (const operation of ["stat", "readdir"]) {
        for (const badRoot of [defaultRoot, configRoot, "both"]) {
          const method = operation === "stat" ? "statSync" : "readdirSync";
          const original = operation === "stat" ? stat : readdir;
          const mock = t.mock.method(fs, method, (file, options) => {
            if (file === badRoot || (badRoot === "both" && [defaultRoot, configRoot].includes(file))) {
              throw Object.assign(new Error("access denied"), { code: "EACCES" });
            }
            return original(file, options);
          });
          try {
            const discover = () => discoverTranscripts({ harnesses: ["claude"], since: "all", strict: true });
            if (badRoot === "both") assert.throws(discover, /unreadable store/);
            else assert.deepEqual(ids(discover()), [badRoot === defaultRoot ? "config" : "default"]);
          } finally {
            mock.mock.restore();
          }
        }
      }
    } finally {
      if (oldHome === undefined) delete process.env.HOME;
      else process.env.HOME = oldHome;
      if (oldConfig === undefined) delete process.env.CLAUDE_CONFIG_DIR;
      else process.env.CLAUDE_CONFIG_DIR = oldConfig;
    }
  });

  it("parses --since windows", () => {
    assert.equal(cutoffMs("all"), 0);
    assert.equal(cutoffMs("2d", 10 * 86400_000), 8 * 86400_000);
    assert.throws(() => cutoffMs("yesterday"), /--since/);
  });
});

describe("OpenCode adapter", () => {
  const home = () => tmpDir("opencode-");

  it("legacy session table prefers time_updated, falls back to time_created, and leaves untimed rows to the cursor", () => {
    const h = home();
    const day = 86400;
    makeSqlite(opencodeDb(h), [
      ["CREATE TABLE session (id TEXT PRIMARY KEY, directory TEXT, time_created INTEGER, time_updated INTEGER)"],
      ["INSERT INTO session VALUES ('fresh', '/tmp/a', ?, ?)", nowSec() - 2 * day, nowSec() - day],
      ["INSERT INTO session VALUES ('stale', '/tmp/b', ?, ?)", nowSec() - 2 * day, nowSec() - 40 * day],
      ["INSERT INTO session VALUES ('created-only', '/tmp/c', ?, NULL)", nowSec() - 5 * day],
      ["INSERT INTO session VALUES ('created-stale', '/tmp/d', ?, NULL)", nowSec() - 60 * day],
    ]);
    const found = discoverTranscripts({ home: h, since: "30d", harnesses: ["opencode"] });
    assert.deepEqual(ids(found).sort(), ["created-only", "fresh"]);
    assert.equal(found.transcripts.find((t) => t.id === "fresh").mtimeMs, (nowSec() - day) * 1000);

    makeSqlite(opencodeDb(h), [["CREATE TABLE session (id TEXT PRIMARY KEY, directory TEXT)"], ["INSERT INTO session VALUES ('no-time', '/tmp/x')"]]);
    const untimed = discoverTranscripts({ home: h, since: "1d", harnesses: ["opencode"] });
    assert.deepEqual(ids(untimed), ["no-time"]);
    assert.equal(untimed.transcripts[0].mtimeMs, null);
  });

  it("reads message events from session_message in order", async () => {
    const h = home();
    makeSqlite(opencodeDb(h), [
      ...OPENCODE_V2,
      ["INSERT INTO session_v2 VALUES ('s', 'p', '/tmp', 't', ?, ?)", nowSec(), nowSec()],
      ["INSERT INTO session_message VALUES ('m2', 's', 'a', 1, 0, 0, ?)", JSON.stringify({ role: "assistant", text: "done" })],
      ["INSERT INTO session_message VALUES ('m1', 's', 'u', 0, 0, 0, ?)", JSON.stringify({ role: "user", text: "please" })],
    ]);
    const [transcript] = discoverTranscripts({ home: h, harnesses: ["opencode"] }).transcripts;
    assert.deepEqual(await readTranscriptEvents(transcript), [
      { kind: "message", role: "user", text: "please" },
      { kind: "message", role: "assistant", text: "done" },
    ]);
  });

  it("normalizes `opencode export` output when SQLite has only session headers", () => {
    const events = opencodeExportToEvents({
      info: { model: { id: "gpt-5.6-terra" } },
      messages: [
        { info: { role: "user" }, parts: [{ type: "text", text: "Investigate the failure" }] },
        {
          info: { role: "assistant" },
          parts: [
            { type: "text", text: "I will inspect the trace." },
            { type: "tool", tool: "read_file", state: { input: { path: "trace.json" }, output: "read ok", status: "completed" } },
          ],
        },
        { info: { role: "system" }, parts: [{ type: "text", text: "ignored" }] },
      ],
    });
    assert.equal(events.model, "gpt-5.6-terra");
    assert.deepEqual(events.events, [
      { kind: "message", role: "user", text: "Investigate the failure" },
      { kind: "message", role: "assistant", text: "I will inspect the trace." },
      { kind: "tool", name: "read_file", input: { path: "trace.json" }, result: "read ok", status: "completed" },
    ]);
  });
});

describe("Hermes adapter schema variants", () => {
  const CURRENT_SESSIONS = "CREATE TABLE sessions (id TEXT PRIMARY KEY, started_at INTEGER, last_activity_at INTEGER, cwd TEXT)";
  const CURRENT_MESSAGES = "CREATE TABLE messages (id TEXT PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, timestamp INTEGER)";

  it("current schema filters by last_activity_at, falling back to started_at", () => {
    const h = tmpDir("hermes-");
    makeSqlite(hermesDb(h), [
      [CURRENT_SESSIONS],
      [CURRENT_MESSAGES],
      ["INSERT INTO sessions VALUES ('recent', ?, ?, '/tmp')", daysAgoSec(29), daysAgoSec(1)],
      ["INSERT INTO sessions VALUES ('stale', ?, ?, '/tmp')", daysAgoSec(90), daysAgoSec(60)],
      ["INSERT INTO sessions VALUES ('started-only', ?, NULL, '/tmp')", daysAgoSec(1)],
      ["INSERT INTO sessions VALUES ('started-stale', ?, NULL, '/tmp')", daysAgoSec(60)],
    ]);
    assert.deepEqual(ids(discoverTranscripts({ home: h, since: "30d", harnesses: ["hermes"] })).sort(), ["recent", "started-only"]);
  });

  it("reads messages.content with roles, and legacy messages.text", async () => {
    const h = tmpDir("hermes-");
    makeSqlite(hermesDb(h), [
      [CURRENT_SESSIONS],
      [CURRENT_MESSAGES],
      ["INSERT INTO sessions VALUES ('s1', ?, ?, '/tmp')", daysAgoSec(1), daysAgoSec(1)],
      ["INSERT INTO messages VALUES ('m1', 's1', 'user', 'hermes content marker', 0)"],
      ["INSERT INTO messages VALUES ('m2', 's1', 'assistant', 'reply here', 0)"],
    ]);
    let [transcript] = discoverTranscripts({ home: h, harnesses: ["hermes"] }).transcripts;
    assert.deepEqual(await readTranscriptEvents(transcript), [
      { kind: "message", role: "user", text: "hermes content marker" },
      { kind: "message", role: "assistant", text: "reply here" },
    ]);

    makeSqlite(hermesDb(h), [
      [CURRENT_SESSIONS],
      ["CREATE TABLE messages (id TEXT PRIMARY KEY, session_id TEXT, role TEXT, text TEXT)"],
      ["INSERT INTO sessions VALUES ('legacy', ?, ?, '/tmp')", daysAgoSec(1), daysAgoSec(1)],
      ["INSERT INTO messages VALUES ('m1', 'legacy', 'user', 'legacy hello')"],
    ]);
    [transcript] = discoverTranscripts({ home: h, harnesses: ["hermes"] }).transcripts;
    assert.deepEqual(await readTranscriptEvents(transcript), [{ kind: "message", role: "user", text: "legacy hello" }]);
  });

  it("timestamp-less sessions survive --since and are left to the cursor", () => {
    const h = tmpDir("hermes-");
    makeSqlite(hermesDb(h), [["CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT)"], ["INSERT INTO sessions VALUES ('notemporal', '/tmp')"]]);
    assert.deepEqual(ids(discoverTranscripts({ home: h, since: "1d", harnesses: ["hermes"] })), ["notemporal"]);
  });

  it("a self session is recognized from its first Hermes message", () => {
    const h = tmpDir("hermes-");
    makeSqlite(hermesDb(h), [
      [HERMES_SESSIONS],
      [HERMES_MESSAGES],
      ["INSERT INTO sessions VALUES ('mine', '/tmp', 'cli', ?, ?)", nowSec(), nowSec()],
      ["INSERT INTO messages VALUES ('m', 'mine', 'user', '<!-- ca-improve:self-session -->\nanalyze')"],
    ]);
    const result = discoverTranscripts({ home: h, harnesses: ["hermes"] });
    assert.deepEqual(ids(result), []);
    assert.equal(result.perHarness.hermes.self, 1);
  });
});

it("codex sessions read their wrapped header and conversation, not the harness preamble", async () => {
  const home = path.join(tmpDir(), "home");
  writeCodexSession(home, "codex-real", { text: "please add the test" });
  const [transcript] = discoverTranscripts({ home, harnesses: ["codex"], since: "all" }).transcripts;
  assert.equal(transcript.id, "codex-real");
  assert.equal(transcript.cwd, "/tmp/proj");
  const events = await readTranscriptEvents(transcript);
  assert.deepEqual(events.filter((e) => e.kind === "message").map((e) => e.text), ["please add the test"]);
  assert.deepEqual(events.filter((e) => e.kind === "tool").map((e) => e.name), ["read", "search", "test"]);
});
