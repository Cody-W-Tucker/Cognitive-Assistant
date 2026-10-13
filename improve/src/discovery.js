// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Discovery mechanism adapted from Backpass src/discovery/index.js and
// src/discovery/adapters/{hermes,pi,claude,codex,opencode}.js (commit
// 0268201), narrowed: global stores only (never CWD-dependent), four
// supported harnesses (hermes/claude/codex/opencode), Pi/Grok/Cursor
// explicitly excluded, header-only reads, fail-soft per store. Pi parsing
// internals (piRoots/discoverFiles pi branch) are retained but never
// selected: Pi sessions are machine/automation work and must not be analyzed.

import fs from "node:fs";
import path from "node:path";
import os from "node:os";

import { HEAD_BYTES, headHasSelfSentinel } from "./sentinel.js";
import { checkpointKey, readSessionCheckpoint } from "./state.js";

/** Harnesses this slice discovers (Pi is excluded; Pi stays valid only as an ACPX agent option). */
export const SUPPORTED_HARNESSES = ["hermes", "claude", "codex", "opencode"];

/** Explicitly out of scope for this slice, with reasons. */
export const EXCLUDED_HARNESSES = {
  pi: "Pi sessions are machine/automation work and must not be analyzed.",
  grok: "Grok transcript store is not mapped in this slice (no stable global format pinned).",
  cursor: "Cursor CLI store is not mapped in this slice.",
  "cursor-ide": "Cursor IDE store is deferred (needs a best-effort preview pass first).",
};

export function resolveHome(override) {
  if (override) return path.resolve(override);
  return process.env.HOME || os.homedir();
}

export function cutoffMs(since, now = Date.now()) {
  if (!since || since === "all") return 0;
  const match = /^(\d+)([hdw])$/.exec(String(since).trim());
  if (!match) throw new Error(`--since: expected like 30d, 12h, 2w, or all (got "${since}")`);
  const n = Number(match[1]);
  const mult = { h: 3600_000, d: 86400_000, w: 7 * 86400_000 }[match[2]];
  return now - n * mult;
}

function statOrNull(p) {
  try {
    return fs.statSync(p);
  } catch {
    return null;
  }
}

function listDirs(dir) {
  try {
    return fs
      .readdirSync(dir, { withFileTypes: true })
      .filter((e) => e.isDirectory())
      .map((e) => path.join(dir, e.name));
  } catch {
    return [];
  }
}

function walkJsonl(root, { depth = 6 } = {}) {
  const out = [];
  const visit = (dir, left) => {
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      if (entry.isFile() && entry.name.endsWith(".jsonl")) out.push(full);
      else if (entry.isDirectory() && left > 0) visit(full, left - 1);
    }
  };
  if (statOrNull(root)?.isDirectory()) visit(root, depth);
  return out.sort();
}

function readFirstLine(file) {
  let fd;
  try {
    fd = fs.openSync(file, "r");
    const stat = fs.fstatSync(fd);
    if (!stat.isFile()) return null;
    const length = Math.min(stat.size, HEAD_BYTES);
    const buffer = Buffer.alloc(length);
    fs.readSync(fd, buffer, 0, length, 0);
    const text = buffer.toString("utf8");
    const line = text.split("\n")[0].trim();
    if (!line) return null;
    try {
      return { header: JSON.parse(line), head: text };
    } catch {
      return { header: null, head: text };
    }
  } catch {
    return null;
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
  }
}

function asAbsolute(value) {
  if (typeof value !== "string" || !value) return null;
  return path.isAbsolute(value) ? value : null;
}

function isUnder(child, parent) {
  if (!child || !parent) return false;
  const a = path.resolve(child);
  const b = path.resolve(parent);
  if (a === b) return true;
  return a.startsWith(b.endsWith(path.sep) ? b : b + path.sep);
}

function firstString(...values) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value;
  }
  return null;
}

// --- file-backed adapters (pi / claude / codex) ----------------------------

function piRoots(home) {
  return [path.join(home, ".pi", "agent", "sessions")];
}

function claudeRoots(home, { isolated = false } = {}) {
  const roots = [path.join(home, ".claude", "projects")];
  if (!isolated && process.env.CLAUDE_CONFIG_DIR) {
    roots.push(path.join(process.env.CLAUDE_CONFIG_DIR, "projects"));
  }
  return [...new Set(roots)];
}

function codexRoots(home, { isolated = false } = {}) {
  if (!isolated && process.env.CODEX_HOME) return [path.join(process.env.CODEX_HOME, "sessions")];
  return [path.join(home, ".codex", "sessions")];
}

function headerCwd(harness, header) {
  if (!header || typeof header !== "object") return null;
  return asAbsolute(header.cwd);
}

function headerId(harness, header, file) {
  const id = firstString(header?.id, header?.sessionId, header?.session_id);
  if (id) return id;
  return `${harness}:${path.basename(file, ".jsonl")}`;
}

function discoverFiles({ harness, roots, stateDir, cutoff }) {
  const stats = { scanned: 0, matched: 0, self: 0, error: null };
  const transcripts = [];
  const seen = readSeenSessions(stateDir);
  let anyRoot = false;
  for (const root of roots) {
    if (!statOrNull(root)?.isDirectory()) continue;
    anyRoot = true;
    for (const file of walkJsonl(root)) {
      const stat = statOrNull(file);
      if (!stat) continue;
      if (cutoff && stat.mtimeMs < cutoff) continue;
      stats.scanned += 1;
      const read = readFirstLine(file);
      if (!read) continue;
      const cwd = headerCwd(harness, read.header);
      if (headHasSelfSentinel(read.head) || isUnder(cwd, stateDir)) {
        stats.self += 1;
        continue;
      }
      const transcriptId = headerId(harness, read.header, file);
      const transcript = {
        harness,
        id: transcriptId,
        cwd,
        path: file,
        mtimeMs: Math.round(stat.mtimeMs),
        self: false,
      };
      if (alreadyProcessed(seen, transcript)) continue;
      transcripts.push(transcript);
      stats.matched += 1;
    }
  }
  if (!anyRoot) stats.error = "store missing";
  return { transcripts, stats };
}

// --- sqlite-backed adapters (opencode / hermes) -----------------------------

async function loadSqlite() {
  try {
    return await import("node:sqlite");
  } catch {
    return null;
  }
}

function tableColumns(db, table) {
  try {
    return db
      .prepare(`PRAGMA table_info(${table})`)
      .all()
      .map((entry) => entry.name);
  } catch {
    return [];
  }
}

function tableNames(db) {
  try {
    return db
      .prepare("SELECT name FROM sqlite_master WHERE type='table'")
      .all()
      .map((row) => row.name);
  } catch {
    return [];
  }
}

function discoverOpencode({ dbPath, stateDir, cutoff }) {
  return discoverSqlite({
    harness: "opencode",
    dbPath,
    stateDir,
    cutoff,
    list: (db) => {
      const tables = new Set(tableNames(db));
      const rows = [];
      if (tables.has("session_v2")) {
        const cols = new Set(tableColumns(db, "session_v2"));
        const hasUpdated = cols.has("time_updated");
        const query = hasUpdated
          ? "SELECT id, directory, title, time_created, time_updated FROM session_v2"
          : "SELECT id, directory, title, time_created FROM session_v2";
        for (const row of db.prepare(query).all()) {
          const mtimeMs = toMs(hasUpdated ? (row.time_updated ?? row.time_created) : row.time_created);
          rows.push({ id: row.id, cwd: asAbsolute(row.directory), mtimeMs, table: "session_v2" });
        }
        const msgCols = tables.has("session_message") ? new Set(tableColumns(db, "session_message")) : new Set();
        if (msgCols.has("data") && msgCols.has("session_id")) {
          const firstText = new Map();
          for (const msg of db
            .prepare("SELECT session_id, data FROM session_message ORDER BY seq ASC")
            .all()) {
            if (!firstText.has(msg.session_id)) firstText.set(msg.session_id, String(msg.data || ""));
          }
          for (const row of rows) row.firstText = firstText.get(row.id) || "";
        }
      } else if (tables.has("session")) {
        const cols = new Set(tableColumns(db, "session"));
        const hasUpdated = cols.has("time_updated");
        const hasCreated = cols.has("time_created");
        const select = ["id", "directory"];
        if (hasUpdated) select.push("time_updated");
        if (hasCreated) select.push("time_created");
        for (const row of db.prepare(`SELECT ${select.join(", ")} FROM session`).all()) {
          const mtimeMs =
            hasUpdated && hasCreated
              ? toMs(row.time_updated ?? row.time_created)
              : hasUpdated
                ? toMs(row.time_updated)
                : hasCreated
                  ? toMs(row.time_created)
                  : null;
          rows.push({ id: row.id, cwd: asAbsolute(row.directory), mtimeMs, table: "session" });
        }
      }
      return rows;
    },
  });
}

function discoverHermes({ dbPath, stateDir, cutoff }) {
  return discoverSqlite({
    harness: "hermes",
    dbPath,
    stateDir,
    cutoff,
    list: (db) => {
      const tables = new Set(tableNames(db));
      if (!tables.has("sessions")) return [];
      const cols = new Set(tableColumns(db, "sessions"));
      const idCol = cols.has("id") ? "id" : [...cols][0];
      const cwdCol = cols.has("cwd") ? "cwd" : null;
      // Timestamp-aware --since: use the committed Hermes temporal columns
      // when present (updated_at preferred, created_at fallback, plus the
      // OpenCode-style time_* aliases). Schemas without any of these keep
      // mtimeMs null so --since cannot guess and the persistent cursor owns
      // freshness instead.
      const updatedCol = ["last_activity_at", "updated_at", "time_updated", "updated", "modified_at"].find((c) =>
        cols.has(c),
      ) || null;
      const createdCol = ["started_at", "created_at", "time_created", "created", "timestamp", "mtime"].find((c) =>
        cols.has(c),
      ) || null;
      const rows = [];
      for (const row of db.prepare(`SELECT * FROM sessions`).all()) {
        const mtimeMs =
          updatedCol && row[updatedCol] != null
            ? toMs(row[updatedCol])
            : createdCol && row[createdCol] != null
              ? toMs(row[createdCol])
              : null;
        rows.push({ id: String(row[idCol]), cwd: cwdCol ? asAbsolute(row[cwdCol]) : null, mtimeMs, table: "sessions" });
      }
      if (tables.has("messages")) {
        const mcols = new Set(tableColumns(db, "messages"));
        const textCol = mcols.has("text") ? "text" : mcols.has("content") ? "content" : null;
        if (mcols.has("session_id") && textCol) {
          const firstText = new Map();
          for (const msg of db.prepare(`SELECT session_id, ${textCol} FROM messages ORDER BY rowid ASC`).all()) {
            const key = String(msg.session_id);
            if (!firstText.has(key)) {
              const raw = msg[textCol];
              const text = Buffer.isBuffer(raw) ? raw.toString("utf8") : String(raw || "");
              firstText.set(key, text);
            }
          }
          for (const row of rows) row.firstText = firstText.get(row.id) || "";
        }
      }
      return rows;
    },
  });
}

function toMs(epochSeconds) {
  const n = Number(epochSeconds);
  if (!Number.isFinite(n)) return null;
  // Heuristic: seconds (< 1e12) vs milliseconds.
  return n < 1e12 ? Math.round(n * 1000) : Math.round(n);
}

function readSeenSessions(stateDir) {
  if (!stateDir) return { processed: {}, legacyIds: new Set() };
  return readSessionCheckpoint(stateDir);
}

function alreadyProcessed(seen, transcript) {
  const prior = seen.processed[checkpointKey(transcript)];
  // Timestamp-less session rows have no reliable mutation signal, so their
  // durable identity is the cursor. Other records re-enter only on revision.
  if (prior !== undefined) return prior === transcript.mtimeMs || prior === null;
  return seen.legacyIds.has(String(transcript.id));
}

function discoverSqliteKind({ harness, dbPath, stateDir, cutoff = 0, seenIds = null, list }) {
  const stats = { scanned: 0, matched: 0, self: 0, error: null };
  const transcripts = [];
  const seen = seenIds instanceof Set ? { processed: {}, legacyIds: seenIds } : readSeenSessions(stateDir);
  if (!statOrNull(dbPath)?.isFile()) {
    stats.error = "store missing";
    return { transcripts, stats };
  }
  let sqlite;
  try {
    sqlite = loadSqliteSync();
  } catch {
    stats.error = "node sqlite unavailable";
    return { transcripts, stats };
  }
  let db;
  try {
    db = new sqlite.DatabaseSync(dbPath, { readOnly: true });
    const rows = list(db);
    for (const row of rows) {
      stats.scanned += 1;

      // --since applies only where the committed schema carries a timestamp
      // (OpenCode time_created/time_updated; Hermes updated_at/created_at or
      // time_* aliases). Rows without temporal columns keep mtimeMs null and
      // are filtered by persistent cursor instead of timestamp guessing.
      if (cutoff && row.mtimeMs != null && row.mtimeMs < cutoff) continue;
      if ((row.firstText && headHasSelfSentinel(row.firstText)) || isUnder(row.cwd, stateDir)) {
        stats.self += 1;
        continue;
      }
      const transcript = {
        harness,
        id: String(row.id),
        cwd: row.cwd || null,
        db: dbPath,
        mtimeMs: row.mtimeMs,
        self: false,
      };
      if (alreadyProcessed(seen, transcript)) continue;
      transcripts.push(transcript);
      stats.matched += 1;
    }
  } catch (err) {
    stats.error = `unreadable store: ${err?.message || err}`;
  } finally {
    try {
      db?.close();
    } catch {
      // ignore close failures on a read-only handle
    }
  }
  return { transcripts, stats };
}

// node:sqlite is ESM-importable synchronously via createRequire-free path;
// use a lazy require through module.createRequire for lowest friction.
import { createRequire } from "node:module";

let cachedSqlite = null;
function loadSqliteSync() {
  if (cachedSqlite) return cachedSqlite;
  cachedSqlite = createRequire(import.meta.url)("node:sqlite");
  return cachedSqlite;
}

function discoverSqlite(options) {
  return discoverSqliteKind(options);
}

/**
 * Discover transcripts from global harness stores (never CWD-dependent).
 *
 * Every harness is fail-soft: a missing/unreadable store yields a named
 * `perHarness[h].error`, never a failed discovery. Sessions carrying the
 * runtime sentinel (or rooted under `stateDir`) are counted as `self` and
 * dropped. Pi/Grok/Cursor are never read; they appear in `excluded`.
 * Pi remains a valid ACPX agent option for production model invocations;
 * it is excluded only from discovery scope.
 */
export function discoverTranscripts({ home, stateDir = null, since = "30d", harnesses = null } = {}) {
  const isolated = home !== undefined && home !== null;
  const root = resolveHome(home);
  const selected = harnesses || SUPPORTED_HARNESSES;
  for (const harness of selected) {
    if (EXCLUDED_HARNESSES[harness]) {
      throw new Error(`harness "${harness}" is ${EXCLUDED_HARNESSES[harness]}`);
    }
    if (!SUPPORTED_HARNESSES.includes(harness)) {
      throw new Error(`unknown harness "${harness}" (supported: ${SUPPORTED_HARNESSES.join(", ")})`);
    }
  }
  const cutoff = cutoffMs(since);
  const transcripts = [];
  const perHarness = {};
  if (stateDir) {
    try {
      fs.mkdirSync(stateDir, { recursive: true });
    } catch {
      // state dir creation is best-effort here; the pipeline owns it
    }
  }
  for (const harness of selected) {
    let found;
    if (harness === "pi") {
      found = discoverFiles({ harness, roots: piRoots(root), stateDir, cutoff });
    } else if (harness === "claude") {
      found = discoverFiles({ harness, roots: claudeRoots(root, { isolated }), stateDir, cutoff });
    } else if (harness === "codex") {
      found = discoverFiles({ harness, roots: codexRoots(root, { isolated }), stateDir, cutoff });
    } else if (harness === "opencode") {
      found = discoverOpencode({
        dbPath: path.join(root, ".local", "share", "opencode", "opencode.db"),
        stateDir,
        cutoff,
      });
    } else if (harness === "hermes") {
      const storeRoot = isolated ? path.join(root, ".hermes") : process.env.HERMES_HOME || path.join(root, ".hermes");
      found = discoverHermes({ dbPath: path.join(storeRoot, "state.db"), stateDir, cutoff });
    }
    perHarness[harness] = found.stats;
    transcripts.push(...found.transcripts);
  }
  transcripts.sort((a, b) => String(a.id).localeCompare(String(b.id)));
  return { transcripts, perHarness, excluded: { ...EXCLUDED_HARNESSES } };
}
