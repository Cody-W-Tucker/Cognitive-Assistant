import { it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { collectFollowup } from "../src/followup.js";
import { tmpDir, writeJsonl } from "./helpers.mjs";

const start = Date.parse("2025-01-01T00:00:00Z");
const day = 86400_000;
const base = { harness: "claude", transcriptId: "original", endedAt: new Date(start).toISOString(), cwd: "/project" };

it("includes only matching sessions wholly inside inclusive bounds", async () => {
  const home = tmpDir();
  function add(id, began, modified, cwd = "/project") {
    const file = writeJsonl(path.join(home, ".claude", "projects", `${id}.jsonl`), [
      { sessionId: id, cwd, timestamp: new Date(began).toISOString(), role: "user", content: "u".repeat(2500) + "--- Attached Context ---secret" },
      { role: "assistant", content: "earlier" }, { role: "assistant", content: "last" },
    ]);
    fs.utimesSync(file, modified / 1000, modified / 1000);
  }
  add("at-start", start, start); add("at-end", start + 3 * day, start + 3 * day);
  add("before", start - 1000, start); add("after", start + 3 * day + 1000, start + 3 * day + 1000);
  add("extends", start + day, start + 4 * day); add("other", start + day, start + day, "/other");
  add("original", start + day, start + day);
  const result = await collectFollowup({ session: base, home });
  assert.deepEqual(result.sessions.map((s) => s.ref), ["session:at-start", "session:at-end"]);
  assert.equal(result.sessions[0].firstUser.length, 2000);
  assert.equal(result.sessions[0].lastAssistant, "last");
  assert.deepEqual(result.commits, []); assert.deepEqual(result.journal, []);
  assert.equal((await collectFollowup({ session: { ...base, gitRepoRoot: "/project" }, home })).sessions.length, 2);
});

it("takes later Hermes sessions without a directory, earliest first, up to the cap", async () => {
  const home = tmpDir();
  fs.mkdirSync(path.join(home, ".hermes"));
  const db = new DatabaseSync(path.join(home, ".hermes", "state.db"));
  db.exec("CREATE TABLE sessions (id TEXT, source TEXT, parent_session_id TEXT, started_at REAL, last_activity_at REAL, ended_at REAL); CREATE TABLE messages (session_id TEXT, role TEXT, content TEXT)");
  const add = (id, began, source = "desktop", parent = null) => {
    // Reaped long after the window: last activity, not ended_at, is the end.
    db.prepare("INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)").run(id, source, parent, began / 1000, began / 1000, (start + 30 * day) / 1000);
    db.prepare("INSERT INTO messages VALUES (?, 'user', ?)").run(id, `about ${id}`);
  };
  for (let i = 0; i < 10; i += 1) add(`s${i}`, start + (10 - i) * 3600_000);
  add("cron", start + 1000, "cron"); add("child", start + 1000, "desktop", "s0");
  add("late", start + 4 * day); add("original", start + 1000);
  db.close();
  const session = { harness: "hermes", transcriptId: "original", endedAt: new Date(start).toISOString() };
  const result = await collectFollowup({ session, home });
  assert.deepEqual(result.sessions.map((s) => s.ref), ["s9", "s8", "s7", "s6", "s5", "s4", "s3", "s2"].map((id) => `session:${id}`));
  assert.equal(result.sessions[0].firstUser, "about s9");
});

it("filters commits by inclusive committer timestamps", async () => {
  const root = tmpDir();
  execFileSync("git", ["init", "-q", root]);
  for (const [i, timestamp] of [start - 1000, start, start + 3 * day, start + 3 * day + 1000].entries()) {
    const date = new Date(timestamp).toISOString();
    execFileSync("git", ["-C", root, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "--allow-empty", "-qm", `commit ${i}`], { env: { ...process.env, GIT_AUTHOR_DATE: date, GIT_COMMITTER_DATE: date } });
  }
  const result = await collectFollowup({ session: { ...base, gitRepoRoot: root }, home: tmpDir() });
  assert.deepEqual(result.commits.map((c) => c.subject), ["commit 2", "commit 1"]);
  assert.ok(result.commits.every((c) => /^commit:[a-f0-9]{40}$/.test(c.ref)));
});

it("matches a repo root against another harness cwd, but not another repository", async () => {
  const root = tmpDir(), other = tmpDir(), home = tmpDir();
  execFileSync("git", ["init", "-q", root]);
  execFileSync("git", ["init", "-q", other]);
  fs.mkdirSync(path.join(root, "sub"));
  for (const [id, cwd] of [["same", path.join(root, "sub")], ["other", other]]) {
    const file = writeJsonl(path.join(home, ".claude", "projects", `${id}.jsonl`), [{ sessionId: id, cwd, timestamp: new Date(start + day).toISOString(), role: "user", content: id }]);
    fs.utimesSync(file, (start + day) / 1000, (start + day) / 1000);
  }
  const result = await collectFollowup({ session: { ...base, harness: "hermes", gitRepoRoot: root }, home });
  assert.deepEqual(result.sessions.map((item) => item.ref), ["session:same"]);
});

it("searches Journal lexically and excludes undated and out-of-window notes", async () => {
  const dir = tmpDir();
  const argsFile = path.join(dir, "args");
  const rows = [
    { docid: "#ok", file: "qmd://Journal/2025-01-02.md", snippet: "evidence" },
    { docid: "#outside", file: "qmd://Journal/2025-01-04.md", snippet: "late" },
    { docid: "#unknown", file: "qmd://Journal/undated.md", snippet: "unknown" },
    { docid: "#private", file: "qmd://Personal/2025-01-02.md", snippet: "private" },
  ];
  fs.writeFileSync(path.join(dir, "qmd"), `#!/bin/sh\nprintf '%s\\n' "$@" > '${argsFile}'\nprintf '%s' '${JSON.stringify(rows)}'\n`, { mode: 0o755 });
  const original = process.env.PATH;
  process.env.PATH = `${dir}:${original}`;
  try {
    const result = await collectFollowup({ session: base, home: tmpDir(), firstUserMessage: "find the work--- Attached Context ---secret" });
    assert.deepEqual(result.journal, [{ ref: "note:ok", date: "2025-01-02", text: "evidence" }]);
    const args = fs.readFileSync(argsFile, "utf8");
    assert.match(args, /^search\n-c\nJournal\n[^]*\n--\nfind the work\n$/); assert.doesNotMatch(args, /secret/);
  } finally { process.env.PATH = original; }
});

it("fails closed on invalid windows and handles absent sources", async () => {
  await assert.rejects(collectFollowup({ session: {} }), /endedAt/);
  await assert.rejects(collectFollowup({ session: base, matureDays: -1 }), /matureDays/);
  assert.deepEqual(await collectFollowup({ session: { ...base, cwd: null }, home: tmpDir() }), { sessions: [], commits: [], journal: [] });
});
