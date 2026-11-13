// Private state for the CA improvement runtime. Everything the runtime
// persists (cursor, evidence, ledger, open gaps, prompts, model cache,
// proposal) lives under the --state-dir Python passes; never in the repo.

import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";

export function initStateDir(stateDir) {
  fs.mkdirSync(path.join(stateDir, "evidence"), { recursive: true });
  fs.mkdirSync(path.join(stateDir, "prompts"), { recursive: true });
}

export function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

/** Parsed JSON, or null when the file is absent or not JSON. */
export function readJson(file) {
  let text;
  try {
    text = fs.readFileSync(file, "utf8");
  } catch (err) {
    if (err.code === "ENOENT") return null;
    throw err;
  }
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/** Sortable, second-resolution stamp used for run and proposal ids. */
export function timestampId(prefix, now = new Date()) {
  return `${prefix}-${now.toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
}

export function shortHash(text) {
  return createHash("sha256").update(String(text)).digest("hex").slice(0, 12);
}

export function slugify(text) {
  return String(text || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "untitled";
}

/** A file-name-safe rendering of an untrusted id. */
function safeName(text) {
  return String(text || "unknown").replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 80) || "unknown";
}

/** Where one session's analysis is kept; separators in the id cannot leave evidence/. */
export function evidenceFile(stateDir, transcriptId) {
  return path.join(stateDir, "evidence", `${String(transcriptId).replace(/[/\\]/g, "_")}.json`);
}

/** Gap identity: the same observation text, ignoring case and spacing. */
export function normalizeQuote(text) {
  return String(text ?? "").toLowerCase().replace(/\s+/g, " ").trim().slice(0, 300);
}

/**
 * Replace stateDir/proposal.json. An unapplied predecessor is kept under
 * proposals/<id>.json so a review in progress is never silently lost;
 * improve-apply additionally refuses decisions bound to a replaced id.
 */
export function writeProposal(stateDir, proposal) {
  const file = path.join(stateDir, "proposal.json");
  const previous = readJson(file);
  if (previous && !previous.appliedAt && previous.id && previous.id !== proposal.id) {
    writeJson(path.join(stateDir, "proposals", `${safeName(previous.id)}.json`), previous);
  }
  writeJson(file, proposal);
}

/**
 * Archive one rendered model prompt as <stateDir>/prompts/<runId>__<name>.md
 * (0600) with a .json sidecar naming the run and stage or session.
 */
export function persistPrompt(stateDir, { runId, name, prompt, meta = {} }) {
  const dir = path.join(stateDir, "prompts");
  fs.mkdirSync(dir, { recursive: true });
  const base = `${safeName(runId)}__${safeName(name)}`;
  const promptFile = path.join(dir, `${base}.md`);
  fs.writeFileSync(promptFile, prompt, { encoding: "utf8", mode: 0o600 });
  const sidecar = { version: 1, runId: String(runId), name: String(name), ...meta, promptFile: `${base}.md`, createdAt: new Date().toISOString() };
  fs.writeFileSync(path.join(dir, `${base}.json`), `${JSON.stringify(sidecar, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  return promptFile;
}

/** A session id is only unique inside one harness store. */
export function checkpointKey(transcript) {
  return `${String(transcript.harness)}:${String(transcript.id)}`;
}

/** harness:id -> session mtime (or null) for every successfully processed session. */
export function readSessionCheckpoint(stateDir) {
  const cursor = readJson(path.join(stateDir, "cursor.json"));
  return cursor?.version === 2 && cursor.processed && typeof cursor.processed === "object" ? cursor.processed : {};
}

/** Successful evidence is the recurrence corpus; raw sessions stay behind the cursor. */
export function readEvidenceRecords(stateDir) {
  const dir = path.join(stateDir, "evidence");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((name) => name.endsWith(".json"))
    .sort()
    .map((name) => readJson(path.join(dir, name)))
    .filter((record) => record?.status === "ok");
}

/** Rows Python appends on reject. A malformed line is skipped; the file stays for audit. */
export function readRejections(stateDir) {
  const file = path.join(stateDir, "rejections.jsonl");
  if (!fs.existsSync(file)) return [];
  const out = [];
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    if (!line.trim()) continue;
    try {
      out.push(JSON.parse(line));
    } catch {
      continue;
    }
  }
  return out;
}

export function assertMinGapEvidence(value, label = "minGapEvidence") {
  const n = Number(value);
  if (!Number.isInteger(n) || n < 2) {
    throw new Error(`${label} must be an integer >= 2 (got ${JSON.stringify(value)})`);
  }
  return n;
}
