// Harness sessions, read from Langfuse. Every supported harness traces one
// root observation per turn, carrying the harness session id as `sessionId`;
// a session is the set of roots sharing it. Tool calls are TOOL observations
// in the same session. Nothing here reads a harness store on disk.

import path from "node:path";
import { createHash } from "node:crypto";

import { langfuseClient } from "./langfuse.js";
import { headHasSelfSentinel } from "./sentinel.js";
import { checkpointKey, readSessionCheckpoint } from "./state.js";

/** Root observation name per harness. */
const ROOT_NAMES = { hermes: "Hermes turn", claude: "Conversational Turn", opencode: "opencode.turn" };

export const SUPPORTED_HARNESSES = Object.keys(ROOT_NAMES);

/** Out of scope, with reasons. Naming one of these is an error, not an empty result. */
const EXCLUDED_HARNESSES = {
  pi: "Pi sessions are machine/automation work and must not be analyzed.",
  codex: "Codex is not traced to Langfuse.",
  grok: "Grok is not traced to Langfuse.",
  cursor: "Cursor is not traced to Langfuse.",
  "cursor-ide": "Cursor IDE is not traced to Langfuse.",
};

/** Langfuse's own evaluator runs appear as roots in this environment. */
const EVALUATOR_ENVIRONMENT = "langfuse-llm-as-a-judge";

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

const ms = (value) => {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
};

/** The harness a root observation belongs to, or null for roots that are not harness turns. */
function harnessOf(observation) {
  if (!observation?.sessionId || observation.environment === EVALUATOR_ENVIRONMENT) return null;
  const harness = SUPPORTED_HARNESSES.find((h) => ROOT_NAMES[h] === observation.name) ?? null;
  // Pi also emits `Conversational Turn`; only Claude Code's belong here.
  if (harness === "claude" && observation.metadata?.source !== "claude-code") return null;
  return harness;
}

function byStart(a, b) {
  return (ms(a.startTime) ?? 0) - (ms(b.startTime) ?? 0) || String(a.id).localeCompare(String(b.id));
}

/**
 * A session's revision: its ordered root ids and end times. A new turn or a
 * late-arriving end time changes it; observations of other sessions do not.
 */
function rootsRevision(harness, id, roots) {
  if (!roots.length) return null;
  const entries = [...roots].sort(byStart).map((root) => [root.id, root.endTime ?? null]);
  return { version: 3, source: "langfuse", harness, id, sha256: createHash("sha256").update(JSON.stringify(entries)).digest("hex") };
}

/** True for a revision this module produced; older ones came from local stores. */
export function isLangfuseRevision(revision) {
  return revision?.source === "langfuse" && revision.version === 3;
}

/** One session's discovery row from its root observations. */
function sessionFromRoots(harness, id, roots) {
  const sorted = [...roots].sort(byStart);
  const starts = sorted.map((root) => ms(root.startTime)).filter((v) => v !== null);
  const ends = sorted.map((root) => ms(root.endTime) ?? ms(root.startTime)).filter((v) => v !== null);
  const metas = sorted.map((root) => root.metadata || {});
  const cwdMeta = metas.find((meta) => typeof meta.cwd === "string" && path.isAbsolute(meta.cwd));
  const platformMeta = metas.find((meta) => typeof meta.platform === "string");
  const cwd = harness === "claude" ? cwdMeta?.cwd ?? null : null;
  return {
    harness,
    id,
    cwd,
    startedAtMs: starts.length ? Math.min(...starts) : null,
    mtimeMs: ends.length ? Math.max(...ends) : null,
    // Langfuse has no session end; the last turn's end is the last activity.
    endedAt: null,
    activityKnown: true,
    source: harness === "hermes" ? platformMeta?.platform ?? null : null,
    gitRepoRoot: null,
    parentSessionId: null,
    revision: rootsRevision(harness, id, sorted),
  };
}

const parse = (value) => {
  if (typeof value !== "string") return value;
  try { return JSON.parse(value); } catch { return value; }
};

/** Plain text from a message, a content part list, or a bare string. */
function textOf(value, depth = 0) {
  if (depth > 4 || value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map((part) => textOf(part, depth + 1)).filter(Boolean).join("\n");
  if (typeof value === "object") {
    if (typeof value.text === "string") return value.text;
    if ("content" in value) return textOf(value.content, depth + 1);
  }
  return "";
}

/** Text of the messages in `io` with `role` (or no role at all, as Hermes output has). */
function roleText(io, role) {
  const value = parse(io);
  if (typeof value === "string") return value;
  const messages = Array.isArray(value) && value.some((m) => m && typeof m === "object" && "role" in m) ? value : [value];
  return messages.filter((m) => !(m && typeof m === "object" && "role" in m) || m.role === role).map((m) => textOf(m)).filter(Boolean).join("\n");
}

function toolResult(output) {
  const value = parse(output);
  if (value === null || value === undefined) return undefined;
  if (typeof value === "string") return value;
  for (const key of ["content", "output", "result", "error"]) if (typeof value[key] === "string") return value[key];
  return JSON.stringify(value);
}

/**
 * Normalize one session's observations into `{kind: message|tool}` events in
 * time order: each turn's user text at its start, its tool calls as they
 * started, its assistant text at its end.
 */
export function observationsToEvents(harness, observations) {
  const roots = [...observations].filter((o) => o.isRootObservation && harnessOf(o) === harness).sort(byStart);
  const turnOf = new Map(roots.map((root, index) => [root.id, index]));
  const seqOf = (o) => {
    if (o.isRootObservation) return turnOf.get(o.id) ?? 0;
    if (o.parentObservationId !== undefined && turnOf.has(o.parentObservationId)) return turnOf.get(o.parentObservationId);
    return roots.length;
  };
  const timed = [];
  [...observations].sort(byStart).forEach((o) => {
    const seq = seqOf(o);
    const start = ms(o.startTime) ?? 0;
    if (o.isRootObservation && harnessOf(o) === harness) {
      const user = roleText(o.input, "user").trim();
      const assistant = roleText(o.output, "assistant").trim();
      if (user) timed.push([start, seq, 0, { kind: "message", role: "user", text: user }]);
      if (assistant) timed.push([ms(o.endTime) ?? start, seq, 2, { kind: "message", role: "assistant", text: assistant }]);
    } else if (o.type === "TOOL") {
      const result = toolResult(o.output);
      timed.push([start, seq, 1, {
        kind: "tool",
        name: String(o.name || "tool").replace(/^Tool:\s*/, ""),
        input: parse(o.input),
        ...(result !== undefined ? { result } : {}),
      }]);
    }
  });
  return timed.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]).map(([, , , event]) => event);
}

let ambient = null;
/** The client from LANGFUSE_* variables, created on first use. */
function clientOr(client) {
  return client ?? (ambient ??= langfuseClient());
}

/**
 * Read one session: its events, its revision (from the same observations),
 * and whether it is the runtime's own session (sentinel on the first turn).
 */
export async function readTranscript(transcript, { client = null } = {}) {
  const observations = (await clientOr(client).observations({ sessionId: transcript.id, fields: "core,basic,io,metadata" })).sort(byStart);
  const roots = observations.filter((o) => o.isRootObservation && harnessOf(o) === transcript.harness);
  if (!roots.length) throw new Error(`session ${transcript.harness}:${transcript.id} not found in Langfuse`);
  const firstInput = roots[0].input;
  return {
    events: observationsToEvents(transcript.harness, observations),
    revision: rootsRevision(transcript.harness, transcript.id, roots),
    self: headHasSelfSentinel(roleText(firstInput, "user").trimStart()) || (typeof firstInput === "string" && headHasSelfSentinel(firstInput)),
  };
}

export async function readTranscriptEvents(transcript, options = {}) {
  return (await readTranscript(transcript, options)).events;
}

/** The session's current revision, from its root observations alone. */
export async function transcriptRevision(transcript, { client = null } = {}) {
  const roots = (await clientOr(client).observations({ sessionId: transcript.id, isRootObservation: true, fields: "core,basic,metadata" }))
    .filter((o) => harnessOf(o) === transcript.harness);
  return rootsRevision(transcript.harness, transcript.id, roots);
}

/**
 * When a session ended, in epoch ms. Last activity wins when known; an
 * explicit end only counts for records written before sessions came from
 * Langfuse.
 */
export function sessionEndMs(session) {
  const explicit = typeof session?.endedAt === "number" ? session.endedAt : Date.parse(session?.endedAt);
  return (session?.activityKnown && session?.mtimeMs) || explicit || null;
}

/**
 * Discover finished sessions with at least one root observation started inside
 * the `since` window. Langfuse has no session end, so a session counts as
 * finished once it has been idle for `idleHours`. Sessions rooted under
 * `stateDir` count as `self` and are dropped (the sentinel check happens on
 * read); sessions the cursor already holds at the same last activity are
 * skipped. A Langfuse failure throws: an unreachable source must never pass
 * as "no sessions".
 */
export async function discoverTranscripts({ client = null, stateDir = null, since = "30d", harnesses = null, idleHours = 12, now = Date.now(), includeCheckpointed = null, ignoreCheckpoint = false, excludeTranscript = null } = {}) {
  if (!Number.isFinite(idleHours) || idleHours < 0) throw new Error("idleHours must be a non-negative number");
  const selected = harnesses || SUPPORTED_HARNESSES;
  for (const harness of selected) {
    if (EXCLUDED_HARNESSES[harness]) throw new Error(`harness "${harness}" is excluded: ${EXCLUDED_HARNESSES[harness]}`);
    if (!ROOT_NAMES[harness]) throw new Error(`unknown harness "${harness}" (supported: ${SUPPORTED_HARNESSES.join(", ")})`);
  }
  const cutoff = cutoffMs(since, now);
  const processed = stateDir && !ignoreCheckpoint ? readSessionCheckpoint(stateDir) : {};
  const transcripts = [];
  const perHarness = {};
  for (const harness of selected) {
    const stats = { scanned: 0, matched: 0, self: 0, open: 0 };
    perHarness[harness] = stats;
    const roots = await clientOr(client).observations({
      isRootObservation: true,
      name: ROOT_NAMES[harness],
      fields: "core,basic,metadata",
      ...(cutoff ? { fromStartTime: new Date(cutoff).toISOString() } : {}),
    });
    const sessions = new Map();
    for (const root of roots) {
      if (harnessOf(root) !== harness) continue;
      if (!sessions.has(root.sessionId)) sessions.set(root.sessionId, []);
      sessions.get(root.sessionId).push(root);
    }
    for (const [id, group] of [...sessions]) {
      if (excludeTranscript?.harness === harness && excludeTranscript.id === id) continue;
      let full = group;
      if (cutoff) {
        full = (await clientOr(client).observations({ sessionId: id, isRootObservation: true, fields: "core,basic,metadata" }))
          .filter((o) => harnessOf(o) === harness);
        if (!full.length) continue;
        sessions.set(id, full);
      }
      const session = sessionFromRoots(harness, id, full);
      stats.scanned += 1;
      if (isUnder(session.cwd, stateDir)) {
        stats.self += 1;
        continue;
      }
      if (session.mtimeMs === null || now - session.mtimeMs <= idleHours * 3600_000) {
        stats.open += 1;
        continue;
      }
      const prior = processed[checkpointKey(session)];
      if (prior !== undefined && (prior === null || prior === session.mtimeMs) && !includeCheckpointed?.(session)) continue;
      transcripts.push(session);
      stats.matched += 1;
    }
  }
  transcripts.sort((a, b) => String(a.id).localeCompare(String(b.id)));
  return { transcripts, perHarness, excluded: { ...EXCLUDED_HARNESSES } };
}
