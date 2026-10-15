// SPDX: MIT — strict synthesis stdout parser (lowest-level shared module).
// Standalone with zero project imports so both acpx-text (helper boundary)
// and synthesize (invoke) can share it without a circular dependency.
// Contract: stdout after whitespace/BOM must be exactly one JSON object
// with exactly `{plans:[...]}` — no prose, no fenced/framed content, no
// trailing content, no extra root keys. Returns the parsed object or null.

/**
 * Strict bounded-synthesis stdout parser (synthesis only).
 * @param {unknown} stdout raw ACPX stdout
 * @returns {{ plans: unknown[] } | null} parsed payload or null when malformed
 */
export function parseStrictBoundedSynthesisStdout(stdout) {
  if (typeof stdout !== "string") return null;
  let text = stdout;
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  const trimmed = text.trim();
  if (!trimmed) return null;
  if (!trimmed.startsWith("{") || !trimmed.endsWith("}")) return null;
  let parsed;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    return null;
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  const keys = Object.keys(parsed);
  if (keys.length !== 1 || keys[0] !== "plans") return null;
  if (!Array.isArray(parsed.plans)) return null;
  return parsed;
}
