// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Adapted from Backpass src/sentinel.js (commit 0268201): the marker-line
// mechanism is the same, but the sentinel text is CA-namespaced so this
// runtime excludes its own sessions rather than Backpass's.

/** First user-message marker every CA improvement prompt starts with. */
export const SELF_SESSION_SENTINEL = "<!-- ca-improve:self-session -->";

/** How much of a transcript's head discovery reads to look for the sentinel. */
export const HEAD_BYTES = 64 * 1024;

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function jsonInner(text) {
  return JSON.stringify(text).slice(1, -1);
}

const SENTINEL_PATTERN = new RegExp(
  `(?:^\\s*|"(?:text|content|message)"\\s*:\\s*")${escapeRegExp(jsonInner(SELF_SESSION_SENTINEL))}`,
);

/** True when `text` (the head of a transcript file) opens with the sentinel. */
export function headHasSelfSentinel(text) {
  return text.startsWith(SELF_SESSION_SENTINEL) || SENTINEL_PATTERN.test(text);
}
