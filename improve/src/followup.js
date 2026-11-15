import fs from "node:fs";
import path from "node:path";
import { execFile, execFileSync } from "node:child_process";
import { promisify } from "node:util";

import { discoverTranscripts, readTranscript } from "./harnesses.js";

const execFileAsync = promisify(execFile);
const DAY_MS = 86400_000;
const MESSAGE_LIMIT = 2000;
const MAX_SESSIONS = 8;
const MAX_TOUCHED = 60;
const MAX_REPOS = 4;
const MAX_COMMITS = 30;
const SOURCES = new Set(["desktop", "tui", "cli"]);

// Do not include attached context, tools, or unbounded transcript text.
function message(text) {
  if (typeof text !== "string") return "";
  return text.split("--- Attached Context ---", 1)[0].trim().slice(0, MESSAGE_LIMIT);
}

function time(value) {
  if (value === null || value === undefined || value === "") return NaN;
  return typeof value === "number" ? value : Date.parse(value);
}

function samePath(a, b) {
  return typeof a === "string" && typeof b === "string" && path.isAbsolute(a) && path.isAbsolute(b) && path.resolve(a) === path.resolve(b);
}

function repoRoot(row) {
  for (const dir of [row.gitRepoRoot, row.cwd]) {
    if (typeof dir !== "string" || !path.isAbsolute(dir)) continue;
    try { return execFileSync("git", ["-C", dir, "rev-parse", "--show-toplevel"], { encoding: "utf8", timeout: 3000, stdio: ["ignore", "pipe", "ignore"] }).trim(); } catch { /* try cwd */ }
  }
  return null;
}

/**
 * Absolute paths named in a session's tool calls (file arguments, shell
 * commands), in first-seen order. Most Hermes sessions record no directory,
 * so this is how the repositories a session worked in are found.
 */
export function touchedPaths(events) {
  const seen = new Set();
  const visit = (value, depth) => {
    if (seen.size >= MAX_TOUCHED || depth > 4) return;
    if (typeof value === "string") {
      for (const [found] of value.matchAll(/(?<![\w.~/-])\/[\w.@+-]+(?:\/[\w.@+-]+)+/g)) {
        if (seen.size < MAX_TOUCHED && found.length <= 300) seen.add(found);
      }
    } else if (value && typeof value === "object") {
      for (const item of Object.values(value)) visit(item, depth + 1);
    }
  };
  for (const event of events || []) if (event?.kind === "tool") visit(event.input, 0);
  return [...seen];
}

/** Repositories to read commits from: the session's own, then those it touched. */
function reposOf(session, touched) {
  const roots = [];
  const tried = new Set();
  const add = (dir) => {
    if (roots.length >= MAX_REPOS || typeof dir !== "string" || !path.isAbsolute(dir) || tried.has(dir)) return;
    tried.add(dir);
    const root = repoRoot({ cwd: dir });
    if (root && !roots.includes(root)) roots.push(root);
  };
  add(repoRoot(session));
  for (const item of Array.isArray(touched) ? touched : []) {
    if (typeof item !== "string") continue;
    // A named file may be new or gone; its directory is what locates the repo.
    add(fs.statSync(item, { throwIfNoEntry: false })?.isDirectory() ? item : path.dirname(item));
  }
  return roots;
}

function noteDate(row) {
  // A date-only note is admissible only if its entire UTC day is in the window.
  const explicit = typeof row.date === "string" ? row.date : "";
  const filename = typeof row.file === "string" ? row.file.split("/").pop() : "";
  const value = explicit || (/^(\d{4}-\d{2}-\d{2})(?:\b|_)/.exec(filename)?.[1] ?? "");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const start = Date.parse(`${value}T00:00:00.000Z`);
  return Number.isFinite(start) && new Date(start).toISOString().slice(0, 10) === value ? start : null;
}

/**
 * Collect bounded, citable evidence. `session` is an evidence record with
 * harness, transcriptId and endedAt; cwd and gitRepoRoot are optional.
 * firstUserMessage must be taken from that session's normalized events, not a
 * full transcript. Returns arrays (empty means none); source failures are
 * intentionally soft.
 *
 * Later sessions: every Hermes session inside the window is a candidate, with
 * no directory requirement (most Hermes sessions have none); the judge decides
 * whether one continues the same aim. Hermes subagent sessions carry the
 * `subagent` platform as their source and are left out. Other harnesses are
 * matched by repo or directory, which only Claude sessions record in Langfuse.
 * The earliest MAX_SESSIONS are kept. `candidates` (an array, or a function
 * returning one or a promise of one) lets a caller discover once for many
 * sessions.
 *
 * Commits: from the session's repository and from the repositories its tool
 * calls touched (`touched`, see touchedPaths), each tagged with its `repo`.
 */
export async function collectFollowup({ session, firstUserMessage = "", matureDays = 3, client = null, stateDir = null, candidates = null, touched = [] } = {}) {
  const start = time(session?.endedAt);
  if (!Number.isFinite(start)) throw new Error("followup: session endedAt is required");
  if (typeof matureDays !== "number" || !Number.isFinite(matureDays) || matureDays < 0) throw new Error("followup: matureDays must be non-negative");
  const end = start + matureDays * DAY_MS;
  if (!Number.isFinite(end) || end > 8640000000000000) throw new Error("followup: invalid window");
  const result = { sessions: [], commits: [], journal: [] };
  const root = repoRoot(session);
  const cwd = session.cwd;

  const located = (typeof root === "string" && path.isAbsolute(root)) || (typeof cwd === "string" && path.isAbsolute(cwd));
  const pool = (typeof candidates === "function" ? await candidates() : candidates)
    ?? (await discoverTranscripts({ client, stateDir, since: "all", ignoreCheckpoint: true })).transcripts;
  const later = [];
  for (const candidate of pool) {
    if (candidate.harness === session.harness && candidate.id === (session.transcriptId ?? session.id)) continue;
    if (candidate.harness === "hermes") {
      if (!SOURCES.has(candidate.source)) continue;
    } else if (!located || (root ? !samePath(root, repoRoot(candidate)) : !samePath(cwd, candidate.cwd))) continue;
    const began = time(candidate.startedAtMs);
    // The last turn's end is the session's end.
    const ended = time(candidate.mtimeMs);
    if (!Number.isFinite(began) || !Number.isFinite(ended) || began < start || began > end || ended < began || ended > end) continue;
    later.push({ candidate, began });
  }
  later.sort((a, b) => a.began - b.began);
  for (const { candidate, began } of later) {
    if (result.sessions.length >= MAX_SESSIONS) break;
    try {
      const { events, self } = await readTranscript(candidate, { client });
      if (self) continue;
      const users = events.filter((e) => e.kind === "message" && e.role === "user" && message(e.text));
      const assistants = events.filter((e) => e.kind === "message" && e.role === "assistant" && message(e.text));
      if (!users.length && !assistants.length) continue;
      result.sessions.push({ ref: `session:${candidate.id}`, harness: candidate.harness, date: new Date(began).toISOString(), firstUser: message(users[0]?.text), lastAssistant: message(assistants.at(-1)?.text) });
    } catch { /* unreadable session */ }
  }

  for (const repo of reposOf(session, touched)) {
    try {
      const { stdout } = await execFileAsync("git", ["-C", repo, "log", "--since-as-filter=" + new Date(start).toISOString(), "--format=%H%x00%cI%x00%s%x00"], { maxBuffer: 4 * 1024 * 1024, timeout: 30000 });
      const fields = stdout.split("\0");
      for (let i = 0; i + 2 < fields.length; i += 3) {
        const hash = fields[i].trim();
        const date = fields[i + 1];
        const at = time(date);
        if (/^[a-f0-9]{40,64}$/.test(hash) && at >= start && at <= end) result.commits.push({ ref: `commit:${hash}`, repo: path.basename(repo), date, subject: message(fields[i + 2]).slice(0, 300) });
      }
    } catch { /* no readable repository */ }
  }
  // A busy repository has more commits than fit: keep those nearest the session.
  result.commits = result.commits.sort((a, b) => time(a.date) - time(b.date)).slice(0, MAX_COMMITS);

  const query = message(firstUserMessage).replace(/\s+/g, " ").slice(0, 500);
  if (query) {
    try {
      const { stdout } = await execFileAsync("qmd", ["search", "-c", "Journal", "--format", "json", "-n", "50", "--", query], { maxBuffer: 4 * 1024 * 1024, timeout: 30000 });
      const rows = JSON.parse(stdout);
      if (Array.isArray(rows)) for (const row of rows) {
        const date = noteDate(row);
        const id = typeof row.docid === "string" ? row.docid.replace(/^#/, "") : "";
        if (date === null || date < start || date + DAY_MS - 1 > end || !/^[a-zA-Z0-9_-]+$/.test(id) || !String(row.file ?? "").startsWith("qmd://Journal/")) continue;
        result.journal.push({ ref: `note:${id}`, date: new Date(date).toISOString().slice(0, 10), text: message(row.snippet) });
      }
    } catch { /* missing qmd, empty or unreadable index */ }
  }
  return result;
}
