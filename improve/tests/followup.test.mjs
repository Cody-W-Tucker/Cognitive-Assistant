import { it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
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
  assert.deepEqual(result.sessions.map((s) => s.ref), ["session:at-end", "session:at-start"]);
  assert.equal(result.sessions[0].firstUser.length, 2000);
  assert.equal(result.sessions[0].lastAssistant, "last");
  assert.deepEqual(result.commits, []); assert.deepEqual(result.journal, []);
  assert.deepEqual((await collectFollowup({ session: { ...base, gitRepoRoot: "/project" }, home })).sessions, []);
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
    assert.match(args, /^search\nfind the work\n-c\nJournal\n/); assert.doesNotMatch(args, /secret/);
  } finally { process.env.PATH = original; }
});

it("fails closed on invalid windows and handles absent sources", async () => {
  await assert.rejects(collectFollowup({ session: {} }), /endedAt/);
  await assert.rejects(collectFollowup({ session: base, matureDays: -1 }), /matureDays/);
  assert.deepEqual(await collectFollowup({ session: { ...base, cwd: null }, home: tmpDir() }), { sessions: [], commits: [], journal: [] });
});
