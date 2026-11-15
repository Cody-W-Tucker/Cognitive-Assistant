import { it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { collectFollowup, touchedPaths } from "../src/followup.js";
import { SELF_SESSION_SENTINEL } from "../src/sentinel.js";
import { tmpDir } from "./helpers.mjs";
import { fakeLangfuse } from "./fake-langfuse.mjs";

const start = Date.parse("2025-01-01T00:00:00Z");
const day = 86400_000;
const base = { harness: "claude", transcriptId: "original", endedAt: new Date(start).toISOString(), cwd: "/project" };

/** One-turn sessions; a turn lasts a minute, so `began` must leave room inside the window. */
function langfuseWith(add) {
  const lf = fakeLangfuse();
  add((harness, id, began, options = {}) => lf.add(harness, id, { start: began, turns: [{ user: options.user ?? `about ${id}`, assistant: options.assistant ?? "last" }], cwd: "/project", ...options }));
  return lf.client;
}

it("includes only matching sessions wholly inside inclusive bounds", async () => {
  const client = langfuseWith((add) => {
    add("claude", "at-start", start, { user: "u".repeat(2500) + "--- Attached Context ---secret" });
    add("claude", "at-end", start + 3 * day - 60_000);
    add("claude", "before", start - 1000);
    add("claude", "extends", start + 3 * day - 30_000);
    add("claude", "other", start + day, { cwd: "/other" });
    add("claude", "original", start + day);
  });
  const result = await collectFollowup({ session: base, client });
  assert.deepEqual(result.sessions.map((s) => s.ref), ["session:at-start", "session:at-end"]);
  assert.equal(result.sessions[0].firstUser.length, 2000);
  assert.equal(result.sessions[0].lastAssistant, "last");
  assert.deepEqual(result.commits, []); assert.deepEqual(result.journal, []);
  assert.equal((await collectFollowup({ session: { ...base, gitRepoRoot: "/project" }, client })).sessions.length, 2);
});

it("takes later Hermes sessions without a directory, earliest first, up to the cap", async () => {
  const client = langfuseWith((add) => {
    for (let i = 0; i < 10; i += 1) add("hermes", `s${i}`, start + (10 - i) * 3600_000);
    add("hermes", "cron", start + 1000, { platform: "cron" });
    add("hermes", "child", start + 1000, { platform: "subagent" });
    add("hermes", "late", start + 4 * day);
    add("hermes", "original", start + 1000);
    add("opencode", "no-dir", start + 1000);
  });
  const session = { harness: "hermes", transcriptId: "original", endedAt: new Date(start).toISOString() };
  const result = await collectFollowup({ session, client });
  assert.deepEqual(result.sessions.map((s) => s.ref), ["s9", "s8", "s7", "s6", "s5", "s4", "s3", "s2"].map((id) => `session:${id}`));
  assert.equal(result.sessions[0].firstUser, "about s9");
});

it("never cites the runtime's own sessions as follow-up", async () => {
  const client = langfuseWith((add) => {
    add("hermes", "later", start + day);
    add("hermes", "self", start + day, { user: `${SELF_SESSION_SENTINEL}\nrun the improvement loop` });
    add("hermes", "original", start);
  });
  const session = { harness: "hermes", transcriptId: "original", endedAt: new Date(start).toISOString() };
  const result = await collectFollowup({ session, client });
  assert.deepEqual(result.sessions.map((s) => s.ref), ["session:later"]);
});

it("filters commits by inclusive committer timestamps", async () => {
  const root = tmpDir();
  execFileSync("git", ["init", "-q", root]);
  for (const [i, timestamp] of [start - 1000, start, start + 3 * day, start + 3 * day + 1000].entries()) {
    const date = new Date(timestamp).toISOString();
    execFileSync("git", ["-C", root, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "--allow-empty", "-qm", `commit ${i}`], { env: { ...process.env, GIT_AUTHOR_DATE: date, GIT_COMMITTER_DATE: date } });
  }
  const result = await collectFollowup({ session: { ...base, gitRepoRoot: root }, candidates: [] });
  assert.deepEqual(result.commits.map((c) => c.subject), ["commit 1", "commit 2"]);
  assert.ok(result.commits.every((c) => /^commit:[a-f0-9]{40}$/.test(c.ref)));
});

it("reads commits from the repositories a session's tool calls touched", async () => {
  const repo = tmpDir(), plain = tmpDir();
  execFileSync("git", ["init", "-q", repo]);
  fs.mkdirSync(path.join(repo, "modules"));
  const date = new Date(start + day).toISOString();
  execFileSync("git", ["-C", repo, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "--allow-empty", "-qm", "apply the change"], { env: { ...process.env, GIT_AUTHOR_DATE: date, GIT_COMMITTER_DATE: date } });
  const touched = touchedPaths([
    { kind: "message", role: "user", text: `not a tool: ${plain}/ignored` },
    { kind: "tool", name: "write_file", input: { path: path.join(repo, "modules", "new-file.nix") } },
    { kind: "tool", name: "terminal", input: { command: `cd ${repo} && ls ${plain}/missing; curl https://example.com/a/b` } },
    { kind: "tool", name: "terminal", input: `cat ${repo}/modules/new-file.nix` },
  ]);
  assert.deepEqual(touched, [path.join(repo, "modules", "new-file.nix"), repo, `${plain}/missing`]);
  // No directory on the session itself, as with most Hermes sessions.
  const session = { harness: "hermes", transcriptId: "original", endedAt: new Date(start).toISOString() };
  const result = await collectFollowup({ session, candidates: [], touched });
  assert.deepEqual(result.commits.map((c) => [c.repo, c.subject]), [[path.basename(repo), "apply the change"]]);
  assert.deepEqual((await collectFollowup({ session, candidates: [] })).commits, []);
});

it("matches a repo root against another harness cwd, but not another repository", async () => {
  const root = tmpDir(), other = tmpDir();
  execFileSync("git", ["init", "-q", root]);
  execFileSync("git", ["init", "-q", other]);
  fs.mkdirSync(path.join(root, "sub"));
  const client = langfuseWith((add) => {
    add("claude", "same", start + day, { cwd: path.join(root, "sub") });
    add("claude", "other", start + day, { cwd: other });
  });
  const result = await collectFollowup({ session: { ...base, harness: "hermes", gitRepoRoot: root }, client });
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
    const result = await collectFollowup({ session: base, candidates: [], firstUserMessage: "find the work--- Attached Context ---secret" });
    assert.deepEqual(result.journal, [{ ref: "note:ok", date: "2025-01-02", text: "evidence" }]);
    const args = fs.readFileSync(argsFile, "utf8");
    assert.match(args, /^search\n-c\nJournal\n[^]*\n--\nfind the work\n$/); assert.doesNotMatch(args, /secret/);
  } finally { process.env.PATH = original; }
});

it("fails closed on invalid windows and handles absent sources", async () => {
  await assert.rejects(collectFollowup({ session: {} }), /endedAt/);
  await assert.rejects(collectFollowup({ session: base, matureDays: -1 }), /matureDays/);
  assert.deepEqual(await collectFollowup({ session: { ...base, cwd: null }, client: fakeLangfuse().client }), { sessions: [], commits: [], journal: [] });
});
