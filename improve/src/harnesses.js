// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Harness adapters adapted from Backpass src/discovery/index.js and
// src/discovery/adapters/{hermes,claude,codex,opencode}.js (commit 0268201),
// narrowed: global stores only (never CWD-dependent), four supported
// harnesses, fail-soft per store. Each adapter both lists sessions and reads
// one session's events, so a store's schema knowledge lives in one place.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";

import { recordToEvents } from "./distill.js";
import { HEAD_BYTES, headHasSelfSentinel } from "./sentinel.js";
import { checkpointKey, readSessionCheckpoint } from "./state.js";

export const SUPPORTED_HARNESSES = ["hermes", "claude", "codex", "opencode"];

/** Out of scope, with reasons. Naming one of these is an error, not an empty result. */
const EXCLUDED_HARNESSES = {
  pi: "Pi sessions are machine/automation work and must not be analyzed.",
  grok: "Grok transcript store is not mapped in this slice (no stable global format pinned).",
  cursor: "Cursor CLI store is not mapped in this slice.",
  "cursor-ide": "Cursor IDE store is deferred (needs a best-effort preview pass first).",
};

export function cutoffMs(since, now = Date.now()) {
  if (!since || since === "all") return 0;
  const match = /^(\d+)([hdw])$/.exec(String(since).trim());
  if (!match) throw new Error(`--since: expected like 30d, 12h, 2w, or all (got "${since}")`);
  return now - Number(match[1]) * { h: 3600_000, d: 86400_000, w: 7 * 86400_000 }[match[2]];
}

function isUnder(child, parent) {
  if (!child || !parent) return false;
  const rel = path.relative(path.resolve(parent), path.resolve(child));
  return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel));
}

function absoluteOrNull(value) {
  return typeof value === "string" && path.isAbsolute(value) ? value : null;
}

/** Epoch seconds or milliseconds to milliseconds. */
function toMs(value) {
  const n = Number(value);
  if (value === null || value === undefined || !Number.isFinite(n)) return null;
  return n < 1e12 ? Math.round(n * 1000) : Math.round(n);
}

// --- JSONL stores (claude, codex) ------------------------------------------

function walkJsonl(root, depth = 6) {
  const out = [];
  const visit = (dir, left) => {
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch (err) {
      if (dir === root) throw err;
      return;
    }
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      if (entry.isFile() && entry.name.endsWith(".jsonl")) out.push(full);
      else if (entry.isDirectory() && left > 0) visit(full, left - 1);
    }
  };
  visit(root, depth);
  return out.sort();
}

function readHead(file) {
  const fd = fs.openSync(file, "r");
  try {
    const buffer = Buffer.alloc(Math.min(fs.fstatSync(fd).size, HEAD_BYTES));
    fs.readSync(fd, buffer, 0, buffer.length, 0);
    return buffer.toString("utf8");
  } finally {
    fs.closeSync(fd);
  }
}

function listJsonlSessions(harness, roots, cutoff, unwrap = (record) => record) {
  const rows = [];
  let readable = false;
  let rootError;
  for (const root of roots) {
    let files;
    try {
      if (!fs.statSync(root, { throwIfNoEntry: false })?.isDirectory()) continue;
      files = walkJsonl(root);
      readable = true;
    } catch (err) {
      rootError = err;
      continue;
    }
    for (const file of files) {
      let head;
      let mtimeMs;
      try {
        mtimeMs = Math.round(fs.statSync(file).mtimeMs);
        if (cutoff && mtimeMs < cutoff) continue;
        head = readHead(file);
      } catch {
        continue; // vanished or unreadable session file; the rest of the store still counts
      }
      let header = null;
      try {
        header = unwrap(JSON.parse(head.split("\n")[0]));
      } catch {
        header = null;
      }
      const id = [header?.id, header?.sessionId, header?.session_id].find((v) => typeof v === "string" && v.trim());
      rows.push({
        id: id || `${harness}:${path.basename(file, ".jsonl")}`,
        cwd: absoluteOrNull(header?.cwd),
        mtimeMs,
        firstText: head,
        location: { path: file },
      });
    }
  }
  if (!readable) {
    if (rootError) throw rootError;
    return null;
  }
  return rows;
}

function readJsonlEvents(transcript, toEvents = recordToEvents) {
  const events = [];
  for (const line of fs.readFileSync(transcript.path, "utf8").split("\n")) {
    if (!line.trim()) continue;
    try {
      events.push(...toEvents(JSON.parse(line)));
    } catch {
      continue; // one torn or foreign line does not void the session
    }
  }
  return events;
}

// Codex rollouts wrap every line as {type, payload}: session_meta carries the
// header, response_item carries messages and tool calls. Developer/system
// preamble, reasoning and tool output are not part of the conversation.
function codexPayload(record) {
  return record?.payload && typeof record.payload === "object" ? record.payload : record;
}

function codexEvents(record) {
  if (record?.type !== "response_item") return [];
  const item = codexPayload(record);
  if (item.type === "message" && (item.role === "user" || item.role === "assistant")) {
    return recordToEvents({ role: item.role, content: item.content });
  }
  if (item.type === "function_call" || item.type === "custom_tool_call") {
    return [{ kind: "tool", name: item.name || "tool", input: item.arguments ?? item.input }];
  }
  return [];
}

// --- SQLite stores (opencode, hermes) --------------------------------------

function openDb(dbPath) {
  const { DatabaseSync } = createRequire(import.meta.url)("node:sqlite");
  return new DatabaseSync(dbPath, { readOnly: true });
}

function withDb(dbPath, fn) {
  const db = openDb(dbPath);
  try {
    return fn(db, schemaOf(db));
  } finally {
    db.close();
  }
}

/** table name -> Set of column names */
function schemaOf(db) {
  const schema = new Map();
  for (const { name } of db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all()) {
    schema.set(name, new Set(db.prepare("SELECT name FROM pragma_table_info(?)").all(name).map((c) => c.name)));
  }
  return schema;
}

const firstOf = (cols, names) => names.find((name) => cols?.has(name)) || null;

function asText(value) {
  return Buffer.isBuffer(value) || value instanceof Uint8Array ? Buffer.from(value).toString("utf8") : String(value ?? "");
}

/**
 * Rows from a sessions table. Timestamps come from the schema's updated
 * column, falling back to its created column; a schema with neither keeps
 * mtimeMs null so --since cannot guess and the cursor owns freshness.
 */
function sessionRows(db, table, cols, { cwdCol, updated, created }) {
  const idCol = cols.has("id") ? "id" : [...cols][0];
  const updatedCol = firstOf(cols, updated);
  const createdCol = firstOf(cols, created);
  return db.prepare(`SELECT * FROM ${table}`).all().map((row) => ({
    id: String(row[idCol]),
    cwd: cwdCol ? absoluteOrNull(row[cwdCol]) : null,
    mtimeMs: toMs(updatedCol ? row[updatedCol] : null) ?? toMs(createdCol ? row[createdCol] : null),
  }));
}

function attachFirstText(rows, firstRows) {
  const first = new Map();
  for (const { session_id: sid, text } of firstRows) if (!first.has(String(sid))) first.set(String(sid), asText(text));
  for (const row of rows) row.firstText = first.get(row.id) || "";
}

const OPENCODE = {
  dbPath: (root) => path.join(root, ".local", "share", "opencode", "opencode.db"),
  list(db, schema) {
    const table = schema.has("session_v2") ? "session_v2" : schema.has("session") ? "session" : null;
    if (!table) return [];
    const rows = sessionRows(db, table, schema.get(table), { cwdCol: "directory", updated: ["time_updated"], created: ["time_created"] });
    const msg = schema.get("session_message");
    if (msg?.has("data") && msg.has("session_id")) {
      attachFirstText(rows, db.prepare("SELECT session_id, data AS text FROM session_message ORDER BY seq ASC").all());
    }
    return rows;
  },
  read(db, schema, sessionId) {
    if (!schema.has("session_message")) return [];
    return db
      .prepare("SELECT data FROM session_message WHERE session_id = ? ORDER BY seq ASC")
      .all(sessionId)
      .flatMap(({ data }) => {
        try {
          return recordToEvents(JSON.parse(asText(data)));
        } catch {
          return [{ kind: "message", role: "user", text: asText(data) }];
        }
      });
  },
};

const HERMES = {
  dbPath: (root, isolated) => path.join(isolated ? path.join(root, ".hermes") : process.env.HERMES_HOME || path.join(root, ".hermes"), "state.db"),
  list(db, schema) {
    const cols = schema.get("sessions");
    if (!cols) return [];
    const rows = sessionRows(db, "sessions", cols, {
      cwdCol: cols.has("cwd") ? "cwd" : null,
      updated: ["last_activity_at", "updated_at", "time_updated", "updated", "modified_at"],
      created: ["started_at", "created_at", "time_created", "created", "timestamp", "mtime"],
    });
    const textCol = firstOf(schema.get("messages"), ["text", "content"]);
    if (textCol && schema.get("messages").has("session_id")) {
      attachFirstText(rows, db.prepare(`SELECT session_id, ${textCol} AS text FROM messages ORDER BY rowid ASC`).all());
    }
    return rows;
  },
  read(db, schema, sessionId) {
    const cols = schema.get("messages");
    const textCol = firstOf(cols, ["text", "content"]);
    if (!textCol || !cols.has("session_id")) return [];
    const roleSelect = cols.has("role") ? "role" : "NULL AS role";
    return db
      .prepare(`SELECT ${roleSelect}, ${textCol} AS text FROM messages WHERE session_id = ? ORDER BY rowid ASC`)
      .all(sessionId)
      .flatMap((row) => recordToEvents({ role: row.role, text: asText(row.text) }));
  },
};

function listSqliteSessions(store, root, isolated) {
  const dbPath = store.dbPath(root, isolated);
  if (!fs.statSync(dbPath, { throwIfNoEntry: false })?.isFile()) return null;
  return withDb(dbPath, (db, schema) => store.list(db, schema)).map((row) => ({ ...row, location: { db: dbPath } }));
}

/** OpenCode `export` output to events (no model call). */
export function opencodeExportToEvents(exported) {
  const events = [];
  for (const message of Array.isArray(exported?.messages) ? exported.messages : []) {
    const role = ["user", "assistant"].includes(message?.info?.role) ? message.info.role : null;
    if (!role) continue;
    for (const part of Array.isArray(message?.parts) ? message.parts : []) {
      if (part?.type === "text" && typeof part.text === "string" && part.text.trim()) {
        events.push({ kind: "message", role, text: part.text });
      } else if (role === "assistant" && part?.type === "tool") {
        const state = part.state && typeof part.state === "object" ? part.state : {};
        const output = typeof state.output === "string" ? state.output : "";
        const error = typeof state.error?.message === "string" ? state.error.message : "";
        events.push({
          kind: "tool",
          name: String(part.tool || part.name || "tool"),
          input: state.input,
          ...(output || error ? { result: [error, output].filter(Boolean).join("\n") } : {}),
          ...(state.status ? { status: state.status } : {}),
        });
      }
    }
  }
  return { events, model: exported?.info?.model?.id || exported?.info?.model?.modelID || null };
}

function readOpencodeExport(sessionId, bin = process.env.CA_IMPROVE_OPENCODE_BIN || "opencode") {
  return new Promise((resolve) => {
    const child = spawn(bin, ["export", String(sessionId)], { stdio: ["ignore", "pipe", "ignore"] });
    let stdout = "";
    const timer = setTimeout(() => child.kill("SIGTERM"), 30_000);
    child.stdout.on("data", (part) => {
      stdout += part;
    });
    child.on("error", () => {
      clearTimeout(timer);
      resolve([]);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      try {
        resolve(code === 0 ? opencodeExportToEvents(JSON.parse(stdout)).events : []);
      } catch {
        resolve([]);
      }
    });
  });
}

const ADAPTERS = {
  claude: {
    list: (root, isolated, cutoff) => {
      const roots = [path.join(root, ".claude", "projects")];
      if (!isolated && process.env.CLAUDE_CONFIG_DIR) roots.push(path.join(process.env.CLAUDE_CONFIG_DIR, "projects"));
      return listJsonlSessions("claude", [...new Set(roots)], cutoff);
    },
    read: readJsonlEvents,
  },
  codex: {
    list: (root, isolated, cutoff) =>
      listJsonlSessions(
        "codex",
        [!isolated && process.env.CODEX_HOME ? path.join(process.env.CODEX_HOME, "sessions") : path.join(root, ".codex", "sessions")],
        cutoff,
        codexPayload,
      ),
    read: (transcript) => readJsonlEvents(transcript, codexEvents),
  },
  opencode: {
    list: (root, isolated) => listSqliteSessions(OPENCODE, root, isolated),
    // OpenCode's current legacy SQLite store can retain only session headers;
    // its export command is then the authoritative read path.
    read: async (transcript) => {
      const events = withDb(transcript.db, (db, schema) => OPENCODE.read(db, schema, transcript.id));
      return events.length ? events : await readOpencodeExport(transcript.id);
    },
  },
  hermes: {
    list: (root, isolated) => listSqliteSessions(HERMES, root, isolated),
    read: (transcript) => withDb(transcript.db, (db, schema) => HERMES.read(db, schema, transcript.id)),
  },
};

/** Events for one discovered transcript. */
export async function readTranscriptEvents(transcript) {
  return await ADAPTERS[transcript.harness].read(transcript);
}

/**
 * Discover sessions from global harness stores (never CWD-dependent).
 *
 * An explicit `home` scopes every store under it; without it the ambient
 * HOME plus HERMES_HOME / CLAUDE_CONFIG_DIR / CODEX_HOME apply. A missing or
 * unreadable store is reported in `perHarness[h].error`; with `strict` (the
 * operator named the harness) it is an error instead, so a misconfigured
 * store cannot pass as "no work". Sessions carrying the runtime sentinel or
 * rooted under `stateDir` count as `self` and are dropped; sessions the
 * cursor already holds at the same revision are skipped.
 */
export function discoverTranscripts({ home, stateDir = null, since = "30d", harnesses = null, strict = false } = {}) {
  const isolated = Boolean(home);
  const root = isolated ? path.resolve(home) : process.env.HOME || os.homedir();
  const selected = harnesses || SUPPORTED_HARNESSES;
  for (const harness of selected) {
    if (EXCLUDED_HARNESSES[harness]) throw new Error(`harness "${harness}" is ${EXCLUDED_HARNESSES[harness]}`);
    if (!ADAPTERS[harness]) throw new Error(`unknown harness "${harness}" (supported: ${SUPPORTED_HARNESSES.join(", ")})`);
  }
  const cutoff = cutoffMs(since);
  const processed = stateDir ? readSessionCheckpoint(stateDir) : {};
  const transcripts = [];
  const perHarness = {};
  for (const harness of selected) {
    const stats = { scanned: 0, matched: 0, self: 0, error: null };
    perHarness[harness] = stats;
    let rows;
    try {
      rows = ADAPTERS[harness].list(root, isolated, cutoff);
    } catch (err) {
      stats.error = `unreadable store: ${err.message}`;
      continue;
    }
    if (rows === null) {
      stats.error = "store missing";
      continue;
    }
    for (const row of rows) {
      if (cutoff && row.mtimeMs !== null && row.mtimeMs < cutoff) continue;
      stats.scanned += 1;
      if ((row.firstText && headHasSelfSentinel(row.firstText)) || isUnder(row.cwd, stateDir)) {
        stats.self += 1;
        continue;
      }
      const transcript = { harness, id: row.id, cwd: row.cwd, ...row.location, mtimeMs: row.mtimeMs };
      // Timestamp-less rows have no mutation signal, so the cursor alone owns them.
      const prior = processed[checkpointKey(transcript)];
      if (prior !== undefined && (prior === null || prior === transcript.mtimeMs)) continue;
      transcripts.push(transcript);
      stats.matched += 1;
    }
  }
  if (strict) {
    const broken = selected.filter((harness) => perHarness[harness].error);
    if (broken.length) throw new Error(broken.map((harness) => `${harness}: ${perHarness[harness].error}`).join("; "));
  }
  transcripts.sort((a, b) => String(a.id).localeCompare(String(b.id)));
  return { transcripts, perHarness, excluded: { ...EXCLUDED_HARNESSES } };
}
