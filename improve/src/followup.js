import path from "node:path";
import { execFile, execFileSync } from "node:child_process";
import { promisify } from "node:util";

import { discoverTranscripts, readTranscriptEvents, transcriptRevision } from "./harnesses.js";

const execFileAsync = promisify(execFile);
const DAY_MS = 86400_000;
const MESSAGE_LIMIT = 2000;
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
 * harness, transcriptId, endedAt, cwd and gitRepoRoot. firstUserMessage must
 * be taken from that session's normalized events, not a full transcript.
 * Returns arrays (empty means none); source failures are intentionally soft.
 */
export async function collectFollowup({ session, firstUserMessage = "", matureDays = 3, home, stateDir, originalLocation = null } = {}) {
  const start = time(session?.endedAt);
  if (!Number.isFinite(start)) throw new Error("followup: session endedAt is required");
  if (typeof matureDays !== "number" || !Number.isFinite(matureDays) || matureDays < 0) throw new Error("followup: matureDays must be non-negative");
  const end = start + matureDays * DAY_MS;
  if (!Number.isFinite(end) || end > 8640000000000000) throw new Error("followup: invalid window");
  const result = { sessions: [], commits: [], journal: [] };
  const root = repoRoot(session);
  const cwd = session.cwd;

  if ((typeof root === "string" && path.isAbsolute(root)) || (typeof cwd === "string" && path.isAbsolute(cwd))) {
    const { transcripts } = discoverTranscripts({ home, stateDir, since: "all", ignoreCheckpoint: true, excludeTranscript: originalLocation ? { ...originalLocation, id: session.transcriptId } : null });
    for (const candidate of transcripts) {
      if (candidate.harness === session.harness && candidate.id === (session.transcriptId ?? session.id)) continue;
      if (candidate.harness === "hermes" && (!SOURCES.has(candidate.source) || candidate.parentSessionId)) continue;
      if (root ? !samePath(root, repoRoot(candidate)) : !samePath(cwd, candidate.cwd)) continue;
      const began = time(candidate.startedAtMs);
      const ended = time(candidate.endedAt ?? candidate.mtimeMs);
      // mtime also guards against a stale endedAt followed by later activity.
      const modified = time(candidate.mtimeMs);
      if (!Number.isFinite(began) || !Number.isFinite(ended) || !Number.isFinite(modified) || began < start || began > end || ended < began || ended > end || modified < began || modified > end) continue;
      try {
        const revision = transcriptRevision(candidate);
        if (!revision) continue;
        const events = await readTranscriptEvents(candidate);
        if (JSON.stringify(revision) !== JSON.stringify(transcriptRevision(candidate))) continue;
        const users = events.filter((e) => e.kind === "message" && e.role === "user" && message(e.text));
        const assistants = events.filter((e) => e.kind === "message" && e.role === "assistant" && message(e.text));
        if (!users.length && !assistants.length) continue;
        result.sessions.push({ ref: `session:${candidate.id}`, harness: candidate.harness, date: new Date(began).toISOString(), firstUser: message(users[0]?.text), lastAssistant: message(assistants.at(-1)?.text) });
      } catch { /* unreadable session */ }
    }
  }

  if (typeof root === "string" && path.isAbsolute(root)) {
    try {
      const { stdout } = await execFileAsync("git", ["-C", root, "log", "--since-as-filter=" + new Date(start).toISOString(), "--format=%H%x00%cI%x00%s%x00"], { maxBuffer: 4 * 1024 * 1024, timeout: 30000 });
      const fields = stdout.split("\0");
      for (let i = 0; i + 2 < fields.length; i += 3) {
        const hash = fields[i].trim();
        const date = fields[i + 1];
        const at = time(date);
        if (/^[a-f0-9]{40,64}$/.test(hash) && at >= start && at <= end) result.commits.push({ ref: `commit:${hash}`, date, subject: message(fields[i + 2]) });
      }
    } catch { /* no readable repository */ }
  }

  const query = message(firstUserMessage).replace(/\s+/g, " ").slice(0, 500);
  if (query) {
    try {
      const { stdout } = await execFileAsync("qmd", ["search", query, "-c", "Journal", "--format", "json", "-n", "50"], { maxBuffer: 4 * 1024 * 1024, timeout: 30000 });
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
