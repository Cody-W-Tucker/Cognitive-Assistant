import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

import { mockInvoke } from "../src/mock.js";

const { DatabaseSync } = createRequire(import.meta.url)("node:sqlite");

export const QUOTE_A = "alpha quote one";
export const QUOTE_B = "beta quote two";

export function tmpDir(prefix = "ca-improve-") {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

export function writeSoul(dir, text = "# SOUL\n\nBe direct.\n") {
  const file = path.join(dir, "SOUL.md");
  fs.writeFileSync(file, text, "utf8");
  return file;
}

export function writeJsonl(file, rows) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${rows.map((r) => JSON.stringify(r)).join("\n")}\n`, "utf8");
  return file;
}

/** Codex rollout lines as Codex writes them: every line wraps a payload. */
export const codex = {
  meta: (id, cwd = "/tmp/proj") => ({ type: "session_meta", payload: { id, cwd } }),
  message: (role, text) => ({
    type: "response_item",
    payload: { type: "message", role, content: [{ type: role === "user" ? "input_text" : "output_text", text }] },
  }),
  tool: (name, input) => ({ type: "response_item", payload: { type: "function_call", name, arguments: JSON.stringify(input) } }),
};

/** A Codex session substantial enough to pass the trivial-session gate. */
export function writeCodexSession(home, id, { text = "bootstrap context please", day = "12" } = {}) {
  const file = path.join(home, ".codex", "sessions", "2026", "10", day, `rollout-${id}.jsonl`);
  writeJsonl(file, [
    codex.meta(id),
    { type: "response_item", payload: { type: "message", role: "developer", content: [{ type: "input_text", text: "harness preamble" }] } },
    codex.message("user", text),
    codex.tool("read", { file_path: "a" }),
    codex.tool("search", { query: "b" }),
    codex.tool("test", { command: "c" }),
  ]);
  return file;
}

export function makeSqlite(dbPath, statements) {
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  fs.rmSync(dbPath, { force: true });
  const db = new DatabaseSync(dbPath);
  for (const [sql, ...params] of statements) db.prepare(sql).run(...params);
  db.close();
}

export const nowSec = () => Math.floor(Date.now() / 1000);
export const daysAgoSec = (days) => nowSec() - days * 86400;

/** One eligible cluster (s1, s2) with distinct per-source quotes, plus an ineligible one. */
export function ledger() {
  return {
    version: 1,
    minGapEvidence: 2,
    clusters: [
      {
        id: "g-aaa",
        proposedInstruction: "Bootstrap context once",
        representativeQuote: QUOTE_A,
        mistake: "sessions re-derive context",
        sources: ["s1", "s2"],
        count: 2,
        eligible: true,
        perSource: { s1: { quote: QUOTE_A, mistake: "m" }, s2: { quote: QUOTE_B, mistake: "m" } },
      },
      {
        id: "g-inelig",
        proposedInstruction: "Ineligible thing",
        representativeQuote: "zzz quote",
        mistake: "m-zzz",
        sources: ["sx"],
        count: 1,
        eligible: false,
        perSource: { sx: { quote: "zzz quote", mistake: "m-zzz" } },
      },
    ],
  };
}

export function evidenceIndex() {
  return new Map([
    ["s1", [{ quote: QUOTE_A, effect: "e1" }]],
    ["s2", [{ quote: QUOTE_B, effect: "e2" }]],
    ["s9", [{ quote: "outsider quote nine", effect: "e9" }]],
  ]);
}

export function record(overrides = {}) {
  return {
    id: "exp-bootstrap-context-a1b2c3d4e5f6",
    title: "Bootstrap context once",
    body: "Recurring gap seen in 2 sessions.",
    sources: ["s1", "s2"],
    clusterId: "g-aaa",
    evidence: [
      { polarity: "negative", text: QUOTE_A, source: "s1", effect: "m" },
      { polarity: "negative", text: QUOTE_B, source: "s2", effect: "m" },
    ],
    counterevidence: "none observed",
    compilerImplication: "compiler appends this record to the experience block",
    ...overrides,
  };
}

export const plan = (overrides = {}) => ({
  id: "e1",
  kind: "add",
  clusterId: "g-aaa",
  provisionalIntent: "Bootstrap context once",
  provisionalSources: ["s1", "s2"],
  provisionalCount: 2,
  ...overrides,
});

/** The mock invoke with some roles replaced; records every call. */
export function invokeWith(overrides = {}) {
  const calls = [];
  const invoke = async (role, prompt, context) => {
    calls.push({ role, prompt });
    return overrides[role] ? overrides[role](context, prompt) : mockInvoke(role, prompt, context);
  };
  invoke.calls = calls;
  return invoke;
}

export function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value)}\n`, "utf8");
}
