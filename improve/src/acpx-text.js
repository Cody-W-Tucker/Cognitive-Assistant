import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";

import { modelForRole } from "./models.js";
import { parseStrictBoundedSynthesisStdout } from "./synthesis-parser.js";
// SPDX: MIT — CA-native ACPX text-output boundary.
// Every production model call goes through the `acpx` binary with ACPX
// text-output requested (`--format quiet`, the upstream Backpass text mode
// from src/acpx.js @ 0268201) — never JSON-RPC (`--format json`, used only
// by `config show`/`status`). This module owns the strict deterministic
// extractor for exactly one final JSON object in ACPX text output, plus the
// shared argv builder with global options before the agent/subcommand and the
// CA_IMPROVE_ACPX_ARGS environment override. No direct model client, no
// OpenCode fallback, no network calls.

/**
 * ACPX text-output flag (upstream `baseArgs` text mode). JSON-RPC mode
 * (`--format json`) is never used for model-final JSON.
 */
export const ACPX_TEXT_FORMAT_ARGS = ["--format", "quiet"];

/**
 * Known ACPX framing line prefix (per-run accounting/status, e.g.
 * `[acpx] tokens: input=10 output=47 ...`). These lines are stripped
 * before extraction; any other surrounding prose is NOT tolerated.
 */
export const ACPX_FRAMING_PREFIX = "[acpx]";

/**
 * Build argv for one ACPX model call (Pi fixed executor, file contract).
 * - Global/environment extra args from CA_IMPROVE_ACPX_ARGS come first
 *   (e.g. `--env KEY=value`), because ACPX globals must precede the
 *   agent/subcommand.
 * - ACPX text-output (`--format quiet`) follows globals and always precedes
 *   the agent. An explicit `--format`/`--output` override via
 *   CA_IMPROVE_ACPX_ARGS is rejected fail-closed (throws) because production
 *   parsing requires ACPX text output; JSON-RPC (`--format json`) is never
 *   parseable here.
 * - Pi is the fixed executor: the callable positional AFTER globals/format
 *   is always `pi` (never another agent). In file mode the canonical tail is
 *   `pi exec --file PROMPTFILE`; prompts travel via the persisted file,
 *   never stdin and never a prompt positional.
 *
 * @param {{ model?: string | null, timeoutSec?: number | null, promptFile?: string | null }} [options]
 * @returns {string[]} argv suitable for spawn; file mode appends --file.
 * @throws {Error} when CA_IMPROVE_ACPX_ARGS overrides --format/--output.
 */
export const ANALYSIS_TIMEOUT_SEC = 180;
export const SYNTHESIS_TIMEOUT_SEC = 300;
export const ROLE_TIMEOUT_SEC = {
  analysis: ANALYSIS_TIMEOUT_SEC,
  consolidate: ANALYSIS_TIMEOUT_SEC,
  synthesis: SYNTHESIS_TIMEOUT_SEC,
  annotate: SYNTHESIS_TIMEOUT_SEC,
};
export const ROLE_AGENT = "pi";
export const ACPX_SPAWN_TIMEOUT_BUFFER_MS = 60_000;

/** Resolve the acpx binary fresh from the environment (selection order). */
export function resolveAcpxBin() {
  return process.env.CA_IMPROVE_ACPX_BIN || process.env.BACKPASS_ACPX_BIN || "acpx";
}

/**
 * Build argv for one ACPX model call.
 * - Global/environment extra args from CA_IMPROVE_ACPX_ARGS come first
 *   (e.g. `--env KEY=value`), because ACPX globals must precede the
 *   agent/subcommand.
 * - ACPX text-output (`--format quiet`) follows globals and always precedes
 *   the agent. An explicit `--format`/`--output` override via
 *   CA_IMPROVE_ACPX_ARGS is rejected fail-closed (throws) because production
 *   parsing requires ACPX text output; JSON-RPC (`--format json`) is never
 *   parseable here.
 * - Pi is the fixed executor: the callable positional AFTER globals/format
 *   is always `pi`, e.g. `acpx --env KEY=value --format quiet pi ...`
 *   (never `acpx pi --format quiet --env KEY=value ...`). No caller may
 *   pass another agent. In file mode the canonical tail is
 *   `pi exec --file PROMPTFILE`.
 * - Explicit `timeoutSec`/`model` are ACPX flags placed AFTER `--format
 *   quiet` and BEFORE the agent (`--timeout N --model M`), so the timeout
 *   is mandatory and ordered before the agent. They replace any same-named
 *   env globals so stages never share one model/timeout. Env-only
 *   timeout/model (no explicit) stay before format for backwards compat.
 * - Explicit `promptFile` appends `exec --file PROMPTFILE` (deduped against
 *   env positionals such as `pi exec`), so prompts travel via a persisted
 *   file, never stdin.
 *
 * @param {{ model?: string | null, timeoutSec?: number | null, promptFile?: string | null }} [options]
 * @returns {string[]} argv suitable for spawn; file mode appends --file.
 * @throws {Error} when CA_IMPROVE_ACPX_ARGS overrides --format/--output,
 *   when a caller passes `agent` (Pi is the fixed executor), or when env
 *   positionals name another executor.
 */
export function buildAcpxArgs(options = {}) {
  if (options && Object.prototype.hasOwnProperty.call(options, "agent")) {
    throw new Error("CA ACPX executor is fixed to pi (caller agent is not accepted)");
  }
  const { model = null, timeoutSec = null, promptFile = null } = options;
  const extra = (process.env.CA_IMPROVE_ACPX_ARGS || "").trim();
  const extraArgs = extra ? extra.split(/\s+/) : [];
  const formatOverride = extraArgs.find(
    (token) =>
      token === "--format" ||
      token === "--output" ||
      token.startsWith("--format=") ||
      token.startsWith("--output="),
  );
  if (formatOverride) {
    throw new Error(
      `CA_IMPROVE_ACPX_ARGS must not override ${formatOverride} (production parsing requires ACPX text output --format quiet)`,
    );
  }
  const flagArgs = [];
  const positionalArgs = [];
  let i = 0;
  while (i < extraArgs.length) {
    const token = extraArgs[i];
    if (!token.startsWith("-")) {
      positionalArgs.push(...extraArgs.slice(i));
      break;
    }
    flagArgs.push(token);
    const next = extraArgs[i + 1];
    if (next !== undefined && !next.startsWith("-")) {
      flagArgs.push(next);
      i += 2;
    } else {
      i += 1;
    }
  }
  const stripOption = (flags, names) => {
    const out = [];
    for (let n = 0; n < flags.length; n += 1) {
      const tok = String(flags[n]);
      if (names.includes(tok)) {
        const next = flags[n + 1];
        if (next !== undefined && !String(next).startsWith("-")) n += 1;
        continue;
      }
      if (names.some((name) => tok.startsWith(`${name}=`))) continue;
      out.push(flags[n]);
    }
    return out;
  };
  let flags = [...flagArgs];
  if (model) flags = stripOption(flags, ["--model"]);
  if (timeoutSec !== null && timeoutSec !== undefined) flags = stripOption(flags, ["--timeout"]);
  if (promptFile) flags = stripOption(flags, ["--file"]);
  for (const token of positionalArgs) {
    if (token !== "pi" && token !== "exec") {
      throw new Error(
        `CA ACPX executor is fixed to pi (CA_IMPROVE_ACPX_ARGS must not name ${JSON.stringify(token)})`,
      );
    }
  }
  const args = [];
  if (flags.length) args.push(...flags);
  args.push(...ACPX_TEXT_FORMAT_ARGS);
  if (timeoutSec !== null && timeoutSec !== undefined) args.push("--timeout", String(timeoutSec));
  if (model) args.push("--model", String(model));
  if (positionalArgs.length) args.push(...positionalArgs);
  if (!positionalArgs.includes("pi")) args.push("pi");
  if (promptFile) {
    if (!args.includes("exec")) args.push("exec");
    args.push("--file", String(promptFile));
  } else if (!positionalArgs.length) {
    // Non-file callers still address the fixed Pi executor explicitly.
    if (!args.includes("pi")) args.push("pi");
  }
  return args;
}

/**
 * Timeout seconds for one pipeline role. Unknown roles fail closed.
 * @param {"analysis"|"consolidate"|"synthesis"|"annotate"} role
 * @returns {number}
 */
export function timeoutForRole(role) {
  const secs = ROLE_TIMEOUT_SEC[String(role)];
  if (!secs) throw new Error(`unknown ACPX timeout role: ${role}`);
  return secs;
}

/**
 * Exactly one shared ACPX invoke helper for the five pipeline stages
 * (analysis, consolidation, synthesis, annotate-preface, annotate).
 * Prompts travel via a persisted `--file` (never stdin); ACPX `--timeout`
 * is mandatory and ordered before the agent; the node spawn timeout stays
 * above the ACPX timeout. Non-synthesis roles extract stdout strictly via
 * extractAcpxFinalJson (exactly one final JSON object, no JSON-RPC, no
 * prose). Role 'synthesis' rejects any workspace/cwd before spawn and
 * strictly validates stdout via the shared synthesis-parser (exactly one
 * JSON object with exactly a plans array); malformed output fails here.
 *
 * @param {{ role: string, promptFile: string, model?: string | null, timeoutSec?: number | null, timeoutMs?: number | null, bin?: string | null, spawnFn?: Function | null }} [options]
 * @returns {{ status: "ok", result: Record<string, unknown>, argv: string[] } | { status: "failed", error: string, argv?: string[] }}
 */
export function runAcpxPromptFile(options = {}) {
  if (options && Object.prototype.hasOwnProperty.call(options, "agent")) {
    throw new Error("CA ACPX executor is fixed to pi (caller agent is not accepted)");
  }
  const { role, promptFile, model = null, timeoutSec = null, timeoutMs = null, bin = null, spawnFn = null, workspace = null, cwd = null } = options;
  const roleKey = String(role || "");
  if (roleKey === "synthesis" && (workspace || cwd)) {
    return { status: "failed", error: "synthesis invoke is text-only: workspace/cwd must not be passed" };
  }
  const workspaceCwd = roleKey === "synthesis" ? null : (workspace || cwd || null);
  let secs = timeoutSec;
  if (secs === null || secs === undefined) {
    secs = ROLE_TIMEOUT_SEC[roleKey];
  }
  if (!secs) {
    return { status: "failed", error: `acpx timeout is required (unknown role ${JSON.stringify(roleKey)})` };
  }
  let mod = model;
  if (!mod) {
    try {
      mod = modelForRole(roleKey);
    } catch {
      return { status: "failed", error: `acpx model is required (unknown role ${JSON.stringify(roleKey)})` };
    }
  }
  const file = promptFile ? String(promptFile) : "";
  if (!file) {
    return { status: "failed", error: "acpx prompt file is required (reuse persisted prompt)" };
  }
  try {
    const stat = fs.statSync(file);
    if (!stat.isFile()) return { status: "failed", error: "acpx prompt file not found" };
  } catch {
    return { status: "failed", error: "acpx prompt file not found" };
  }
  const effectiveBin = bin || resolveAcpxBin();
  let argv;
  try {
    argv = buildAcpxArgs({ model: mod, timeoutSec: secs, promptFile: file });
  } catch (err) {
    return { status: "failed", error: err?.message || String(err) };
  }
  const spawn = spawnFn || spawnSync;
  const spawnTimeout =
    timeoutMs !== null && timeoutMs !== undefined ? timeoutMs : Number(secs) * 1000 + ACPX_SPAWN_TIMEOUT_BUFFER_MS;
  const spawnOpts = { encoding: "utf8", timeout: spawnTimeout, ...(workspaceCwd ? { cwd: String(workspaceCwd) } : {}) };
  const result = spawn(effectiveBin, argv, spawnOpts);
  if (result?.error || result?.status !== 0) {
    return { status: "failed", error: result?.error?.message || `acpx exit ${result?.status}`, argv };
  }
  const stdout = result?.stdout ?? "";
  if (roleKey === "synthesis") {
    // Synthesis is strict at this helper boundary: stdout must be exactly
    // one JSON object with exactly {plans:[...]} (shared parser). Malformed
    // prose/fenced/trailing/extra-key output fails here, never ok/raw.
    const raw = String(stdout ?? "");
    const parsed = parseStrictBoundedSynthesisStdout(raw);
    if (!parsed) {
      return { status: "failed", error: "acpx synthesis returned malformed payload (expected {plans:[...]})", argv };
    }
    return { status: "ok", stdout: raw, result: parsed, argv };
  }
  const parsed = extractAcpxFinalJson(stdout);
  if (!parsed) {
    return { status: "failed", error: "acpx returned unparseable output", argv };
  }
  return { status: "ok", result: parsed, argv };
}

/** Non-blocking ACPX boundary for parallel trace analysis. */
export async function runAcpxPromptFileAsync({ role, promptFile, model = null, timeoutSec = null, bin = null, workspace = null, cwd = null, spawnFn = null } = {}) {
  const roleKey = String(role || "");
  if (roleKey === "synthesis" && (workspace || cwd)) {
    return { status: "failed", error: "synthesis invoke is text-only: workspace/cwd must not be passed" };
  }
  const workspaceCwd = roleKey === "synthesis" ? null : (workspace || cwd || null);
  const secs = timeoutSec ?? ROLE_TIMEOUT_SEC[roleKey];
  if (!secs) return { status: "failed", error: `acpx timeout is required (unknown role ${JSON.stringify(roleKey)})` };
  try { if (!promptFile || !fs.statSync(promptFile).isFile()) return { status: "failed", error: "acpx prompt file not found" }; } catch { return { status: "failed", error: "acpx prompt file not found" }; }
  let argv;
  try { argv = buildAcpxArgs({ model: model || modelForRole(String(role)), timeoutSec: secs, promptFile }); } catch (err) { return { status: "failed", error: err?.message || String(err) }; }
  return await new Promise((resolve) => {
    let child;
    const spawner = spawnFn || spawn;
    const spawnOpts = { stdio: ["ignore", "pipe", "pipe"], ...(workspaceCwd ? { cwd: String(workspaceCwd) } : {}) };
    try { child = spawner(bin || resolveAcpxBin(), argv, spawnOpts); } catch (err) { resolve({ status: "failed", error: err?.message || String(err), argv }); return; }
    let stdout = "", stderr = "", expired = false;
    const timer = setTimeout(() => { expired = true; child.kill("SIGTERM"); }, Number(secs) * 1000 + ACPX_SPAWN_TIMEOUT_BUFFER_MS);
    child.stdout.on("data", (part) => { stdout += part; }); child.stderr.on("data", (part) => { stderr += part; });
    child.on("error", (err) => { clearTimeout(timer); resolve({ status: "failed", error: err.message, argv }); });
    child.on("close", (code) => { clearTimeout(timer); if (expired || code !== 0) { resolve({ status: "failed", error: expired ? "acpx timed out" : (stderr.trim() || `acpx exit ${code}`), argv }); return; } if (roleKey === "synthesis") { const raw = String(stdout ?? ""); const parsed = parseStrictBoundedSynthesisStdout(raw); if (!parsed) { resolve({ status: "failed", error: "acpx synthesis returned malformed payload (expected {plans:[...]})", argv }); return; } resolve({ status: "ok", stdout: raw, result: parsed, argv }); return; } const parsed = extractAcpxFinalJson(stdout); resolve(parsed ? { status: "ok", result: parsed, argv } : { status: "failed", error: "acpx returned unparseable output", argv }); });
  });
}

/**
 * True for known ACPX framing lines stripped before extraction.
 * @param {string} line
 * @returns {boolean}
 */
export function isAcpxFramingLine(line) {
  return String(line).startsWith(ACPX_FRAMING_PREFIX);
}

/**
 * Strip known ACPX framing lines (`[acpx] ...`) from raw stdout.
 * @param {string} text
 * @returns {string}
 */
export function stripAcpxFraming(text) {
  return String(text || "")
    .split("\n")
    .filter((line) => !isAcpxFramingLine(line))
    .join("\n");
}

/**
 * Known Pi quiet-mode preamble stripped before extraction.
 * Real Pi (`exit 0`, exactly one JSON evidence object) may prefix the final
 * object with this deterministic shape only:
 *   pi v<version>
 *   <separator of `-`/`=`/`─`/`—`, >=3 chars>
 *   blank line(s)
 *   Context heading + `-`/`*` bullet list (>=1 item)
 *   Skills heading + `-`/`*` bullet list (>=1 item)
 * Headings are exactly `Context`/`Skills` or level-2 `## Context`/`## Skills`
 * (optional trailing colon).
 * Preamble lines must not contain `{`, `}`, or fences, and the remainder
 * after the preamble must start with `{` or ``` — otherwise no stripping
 * occurs and existing fail-closed extraction rejects the output.
 * An optional upgrade-notice tail is tolerated after the Skills list only:
 * blank line(s), one separator line of 3+ hyphens (`---`), blank line(s),
 * exactly one notice line starting `New version available:`, blank line(s),
 * then the final JSON. Any other prose, unknown notice, extra line, or
 * second notice falls through fail-closed (no stripping).
 * @param {string} text
 * @returns {string} remainder after the preamble, or the input unchanged
 */
export function stripPiQuietPreamble(text) {
  const src = String(text || "");
  const lines = src.split("\n");
  const clean = (line) => String(line ?? "").replace(/\r$/, "");
  const isBlank = (line) => clean(line).trim() === "";
  const isBullet = (line) => {
    const c = clean(line);
    if (/[{}`]/.test(c) || c.includes("```")) return false;
    return /^\s*[-*]\s+\S.*$/.test(c);
  };
  let i = 0;
  while (i < lines.length && isBlank(lines[i])) i += 1;
  const versionLine = clean(lines[i] ?? "");
  if (!/^pi v[0-9A-Za-z._-]+$/.test(versionLine)) return src;
  if (/[{}`]/.test(versionLine) || versionLine.includes("```")) return src;
  i += 1;
  const separator = clean(lines[i] ?? "").trim();
  if (!/^[-—─=]{3,}$/.test(separator)) return src;
  i += 1;
  while (i < lines.length && isBlank(lines[i])) i += 1;
  if (!/^(?:##\s+)?Context:?$/.test(clean(lines[i] ?? "").trim())) return src;
  i += 1;
  let count = 0;
  while (i < lines.length && isBullet(lines[i])) {
    count += 1;
    i += 1;
  }
  if (count < 1) return src;
  while (i < lines.length && isBlank(lines[i])) i += 1;
  if (!/^(?:##\s+)?Skills:?$/.test(clean(lines[i] ?? "").trim())) return src;
  i += 1;
  count = 0;
  while (i < lines.length && isBullet(lines[i])) {
    count += 1;
    i += 1;
  }
  if (count < 1) return src;
  while (i < lines.length && isBlank(lines[i])) i += 1;
  // Optional upgrade-notice tail: blank(s) already skipped, then one
  // hyphen-only separator (3+), blank(s), exactly one upgrade notice,
  // blank(s), then JSON. Anything else stays on the strict path below.
  if (/^-{3,}$/.test(clean(lines[i] ?? "").trim())) {
    i += 1;
    while (i < lines.length && isBlank(lines[i])) i += 1;
    const notice = clean(lines[i] ?? "");
    if (!notice.trimStart().startsWith("New version available:")) return src;
    if (/[{}]/.test(notice) || notice.includes("```")) return src;
    i += 1;
    while (i < lines.length && isBlank(lines[i])) i += 1;
  }
  const remainder = lines.slice(i).join("\n");
  const remainderStart = remainder.trimStart().replace(/^\uFEFF/, "");
  if (remainderStart.startsWith("{") || remainderStart.startsWith("```")) return remainder;
  return src;
}

/**
 * True when the parsed object is a JSON-RPC envelope, which is never a
 * valid model-final payload. Any object carrying a `jsonrpc` member is
 * rejected fail-closed.
 * @param {unknown} value
 * @returns {boolean}
 */
export function isJsonRpcEnvelope(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  return Object.prototype.hasOwnProperty.call(value, "jsonrpc");
}

/**
 * Scan for top-level balanced `{...}` object spans, string-aware
 * (handles `"..."`, `\\` escapes). No regex heuristics.
 * @param {string} text
 * @returns {{ start: number, end: number }[]}
 */
function scanObjectSpans(text) {
  const spans = [];
  const src = String(text);
  let depth = 0;
  let start = -1;
  let inString = false;
  let escaped = false;
  for (let i = 0; i < src.length; i += 1) {
    const ch = src[i];
    if (inString) {
      if (escaped) {
        escaped = false;
      } else if (ch === "\\") {
        escaped = true;
      } else if (ch === '"') {
        inString = false;
      }
      continue;
    }
    if (ch === '"') {
      inString = true;
      continue;
    }
    if (ch === "{") {
      if (depth === 0) start = i;
      depth += 1;
    } else if (ch === "}") {
      if (depth > 0) {
        depth -= 1;
        if (depth === 0 && start !== -1) {
          spans.push({ start, end: i });
          start = -1;
        }
      } else {
        // Unbalanced close brace outside any object: malformed.
        return [];
      }
    }
  }
  if (depth !== 0 || inString) return [];
  return spans;
}

/**
 * Unwrap a single fenced code block. Returns null when fenced but invalid:
 * more than one fenced block, missing fences, or content outside the fence
 * beyond whitespace. Uses string operations only (no loose regex).
 * @param {string} trimmed
 * @returns {{ fenced: boolean, inner: string } | null}
 */
function unwrapSingleFence(trimmed) {
  const FENCE = "```";
  const first = trimmed.indexOf(FENCE);
  if (first === -1) return { fenced: false, inner: trimmed };
  const last = trimmed.lastIndexOf(FENCE);
  if (last === first) return null;
  // More than two fence markers means multiple/ambiguous blocks.
  const third = trimmed.indexOf(FENCE, first + FENCE.length);
  if (third !== -1 && third !== last) return null;
  const before = trimmed.slice(0, first).trim();
  const after = trimmed.slice(last + FENCE.length).trim();
  if (before !== "" || after !== "") return null;
  let inner = trimmed.slice(first + FENCE.length, last);
  // Optional single info string (`json` or `JSON`) on the opening line.
  if (inner.startsWith("json") || inner.startsWith("JSON")) {
    const rest = inner.slice(4);
    if (rest !== "" && !/^\s/.test(rest)) return null;
    inner = rest;
  } else if (/^[A-Za-z]/.test(inner.trimStart().slice(0, 1)) && !/^\s/.test(inner)) {
    // A non-json info string (e.g. ```python) is not tolerated.
    const head = inner.trimStart().split(/\s/, 1)[0];
    if (head !== "") return null;
  }
  return { fenced: true, inner };
}

/**
 * Backpass-compatible deterministic extractor for one JSON object in ACPX text
 * output. ACPX/OpenCode may add prose or fenced formatting around its final
 * object; Backpass deliberately unwraps that transport decoration. CA keeps
 * object-only and JSON-RPC rejection, but otherwise follows its order: first
 * fenced candidate, then the full cleaned reply; try whole JSON, then the span
 * from its first `{` through its last `}`.
 *
 * @param {string} stdout raw ACPX stdout (text-output mode)
 * @returns {Record<string, unknown> | null} the final object or null
 */
export function extractAcpxFinalJson(stdout) {
  if (typeof stdout !== "string") return null;
  let text = stdout;
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  text = stripAcpxFraming(text).trim();
  if (!text) return null;
  text = stripPiQuietPreamble(text).trim();
  if (!text) return null;

  const fenced = /```(?:json)?\s*([\s\S]*?)```/i.exec(text);
  const candidates = [];
  if (fenced) candidates.push(fenced[1]);
  candidates.push(text);
  for (const raw of candidates) {
    const candidate = raw.trim();
    const forms = [candidate];
    const first = candidate.indexOf("{");
    const last = candidate.lastIndexOf("}");
    if (first !== -1 && last > first) forms.push(candidate.slice(first, last + 1));
    for (const form of forms) {
      let parsed;
      try {
        parsed = JSON.parse(form);
      } catch {
        continue;
      }
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed) || isJsonRpcEnvelope(parsed)) continue;
      return parsed;
    }
  }
  return null;
}
