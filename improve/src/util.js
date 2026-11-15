// Small helpers shared by several stages.

import { createHash } from "node:crypto";

export const DAY_MS = 86400_000;
export const ATTACHED_MARKER = "--- Attached Context ---";

export const sha256 = (value) => createHash("sha256").update(value).digest("hex");

/** Whitespace flattened to single spaces, cut at `limit` with a trailing `...`. */
export function oneLine(text, limit) {
  const flat = String(text ?? "").replace(/\s+/g, " ").trim();
  return flat.length > limit ? `${flat.slice(0, limit)}...` : flat;
}

/** Epoch ms from a number or a date string; NaN when absent. */
export function time(value) {
  if (value === null || value === undefined || value === "") return NaN;
  return typeof value === "number" ? value : Date.parse(value);
}

/** `fn` over `items` with at most `jobs` (default 4) in flight; results keep input order. */
export async function mapPool(items, jobs, fn) {
  const out = new Array(items.length);
  let next = 0;
  const worker = async () => {
    while (next < items.length) {
      const index = next++;
      out[index] = await fn(items[index]);
    }
  };
  await Promise.all(Array.from({ length: Math.max(1, Math.min(Number(jobs) || 4, items.length)) }, worker));
  return out;
}
