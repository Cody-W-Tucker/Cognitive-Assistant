// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Deterministic distillation adapted from Backpass src/distill.js (commit
// 0268201): keep the human/agent signal, one-line tool shapes, drop
// boilerplate. No model involved.

const TOOL_INPUT_CHARS = 160;
const TOOL_OUTPUT_CHARS = 200;
const MESSAGE_CHARS = 6000;

function oneLine(text, limit) {
  const flat = String(text ?? "").replace(/\s+/g, " ").trim();
  return flat.length > limit ? `${flat.slice(0, limit)}...` : flat;
}

function clampMessage(text) {
  const trimmed = String(text ?? "").trim();
  if (trimmed.length <= MESSAGE_CHARS) return trimmed;
  const head = trimmed.slice(0, MESSAGE_CHARS - 1200);
  const tail = trimmed.slice(-1000);
  return `${head}\n\n[... ${trimmed.length - MESSAGE_CHARS} chars elided ...]\n\n${tail}`;
}

function describeToolInput(input) {
  if (input === null || input === undefined) return "";
  if (typeof input === "string") return oneLine(input, TOOL_INPUT_CHARS);
  for (const key of ["command", "cmd", "file_path", "path", "pattern", "query", "url", "description"]) {
    if (typeof input[key] === "string" && input[key].trim()) {
      return oneLine(input[key], TOOL_INPUT_CHARS);
    }
  }
  try {
    return oneLine(JSON.stringify(input), TOOL_INPUT_CHARS);
  } catch {
    return "";
  }
}

const BOILERPLATE = [
  /^<system-reminder>/,
  /^<user_info>/,
  /^<recommended_plugins>/,
  /^<permissions instructions>/,
  /^<env>/,
  /^Caveat: The messages below were generated/,
];

export function isBoilerplate(text) {
  const trimmed = String(text ?? "").trim();
  if (!trimmed) return true;
  return BOILERPLATE.some((re) => re.test(trimmed));
}

/**
 * Normalized events accepted:
 *   { kind: 'message', role: 'user'|'assistant', text }
 *   { kind: 'tool', name, input, result }
 * Thinking/reasoning events are dropped (noise for this purpose).
 */
export function distill(events, meta = {}) {
  const lines = [];
  lines.push(`# session ${meta.id || "unknown"} (${meta.harness || "unknown"})`);
  if (meta.cwd) lines.push(`cwd: ${meta.cwd}`);
  lines.push("");
  for (const event of events || []) {
    if (!event || typeof event !== "object") continue;
    if (event.kind === "message") {
      const text = clampMessage(event.text);
      if (isBoilerplate(text)) continue;
      const role = event.role === "assistant" ? "agent" : "human";
      lines.push(`## ${role}`);
      lines.push(text);
      lines.push("");
    } else if (event.kind === "tool") {
      const input = describeToolInput(event.input);
      lines.push(`- tool ${event.name || "unknown"}${input ? `: ${input}` : ""}`);
    }
  }
  lines.push(`source: ${meta.path || meta.db || "unknown"}`);
  return lines.join("\n").slice(0, 24000);
}

/** Best-effort normalization of one raw transcript record into events. */
export function recordToEvents(record) {
  if (!record || typeof record !== "object") return [];
  if (record.kind === "message" || record.kind === "tool") return [record];
  // Generic harness JSON shapes: pick the first recognizable text field.
  const text =
    record.content ??
    record.text ??
    record.message?.content ??
    record.data?.text ??
    null;
  const role = record.role || record.message?.role || record.type;
  if (typeof text === "string") {
    const normalizedRole = role === "assistant" ? "assistant" : "user";
    return [{ kind: "message", role: normalizedRole, text }];
  }
  if (Array.isArray(text)) {
    const parts = text.filter((p) => typeof p?.text === "string").map((p) => p.text);
    if (parts.length) {
      const normalizedRole = role === "assistant" ? "assistant" : "user";
      return [{ kind: "message", role: normalizedRole, text: parts.join("\n") }];
    }
  }
  if (record.tool || record.name) {
    return [{ kind: "tool", name: record.name || record.tool, input: record.input ?? record.args }];
  }
  return [];
}
