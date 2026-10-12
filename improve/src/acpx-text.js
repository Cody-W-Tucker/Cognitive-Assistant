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
 * Build argv for one ACPX model call.
 * - Global/environment extra args from CA_IMPROVE_ACPX_ARGS come first
 *   (e.g. `--env KEY=value`), because ACPX globals must precede the
 *   agent/subcommand.
 * - ACPX text-output (`--format quiet`) follows globals and always precedes
 *   the agent. An explicit `--format`/`--output` override via
 *   CA_IMPROVE_ACPX_ARGS is rejected fail-closed (throws) because production
 *   parsing requires ACPX text output; JSON-RPC (`--format json`) is never
 *   parseable here.
 * - Explicit caller `agent` (including `pi`) stays the callable positional
 *   AFTER globals/format, so spawn appends prompt/input after it, e.g.
 *   `acpx --env KEY=value --format quiet pi ...` (never
 *   `acpx pi --format quiet --env KEY=value ...`).
 * - Extra non-format args come verbatim from CA_IMPROVE_ACPX_ARGS
 *   (whitespace-split): leading `-`-flag groups with their values stay
 *   before format as globals, bare positional subcommands such as
 *   `pi exec` follow format and precede the agent.
 *
 * @param {{ agent?: string | null }} [options]
 * @returns {string[]} argv suitable for spawn; downstream appends prompt/input.
 * @throws {Error} when CA_IMPROVE_ACPX_ARGS overrides --format/--output.
 */
export function buildAcpxArgs({ agent = null, model = null } = {}) {
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
  const args = [];
  if (flagArgs.length) args.push(...flagArgs);
  // Role model is a global ACPX flag. Env args may already set --model;
  // an explicit role model replaces that so stages do not share one model.
  if (model) {
    const withoutModel = [];
    for (let n = 0; n < args.length; n += 1) {
      if (args[n] === "--model") {
        n += 1;
        continue;
      }
      if (String(args[n]).startsWith("--model=")) continue;
      withoutModel.push(args[n]);
    }
    args.length = 0;
    args.push(...withoutModel, "--model", String(model));
  }
  args.push(...ACPX_TEXT_FORMAT_ARGS);
  if (positionalArgs.length) args.push(...positionalArgs);
  if (agent) args.push(String(agent));
  return args;
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
 * Strict deterministic extractor for exactly one final JSON object in ACPX
 * text output. Tolerates ONLY known ACPX framing (`[acpx] ...` lines),
 * one known Pi quiet preamble (version/separator/Context/Skills shape,
 * plus an optional upgrade-notice tail: one 3+ hyphen separator and one
 * `New version available:` line),
 * surrounding whitespace, and one optional ```json fenced block.
 * Fail-closed (returns null) on: absent/malformed JSON, unbalanced braces,
 * zero or ambiguous (>=2) top-level object candidates, top-level
 * arrays/scalars, JSON-RPC envelopes, non-object finals, any model prose
 * or arbitrary embedded JSON outside the single final object.
 *
 * @param {string} stdout raw ACPX stdout (text-output mode)
 * @returns {Record<string, unknown> | null} the single final object or null
 */
export function extractAcpxFinalJson(stdout) {
  if (typeof stdout !== "string") return null;
  // Strip BOM when present.
  let text = stdout;
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  text = stripAcpxFraming(text).trim();
  if (!text) return null;
  text = stripPiQuietPreamble(text).trim();
  if (!text) return null;

  const unwrapped = unwrapSingleFence(text);
  if (unwrapped === null) return null;
  const candidate = unwrapped.inner.trim();
  if (!candidate) return null;

  // Top-level arrays/scalars can never be model-final JSON.
  if (candidate[0] !== "{") return null;

  const spans = scanObjectSpans(candidate);
  if (spans.length !== 1) return null;
  const span = spans[0];
  // The single object must be the entire payload (whitespace only outside).
  if (candidate.slice(0, span.start).trim() !== "") return null;
  if (candidate.slice(span.end + 1).trim() !== "") return null;

  let parsed = null;
  try {
    parsed = JSON.parse(candidate.slice(span.start, span.end + 1));
  } catch {
    return null;
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  if (isJsonRpcEnvelope(parsed)) return null;
  return parsed;
}
