// The active SOUL (the one Hermes runs) is read-only context for every
// proposal. Missing or empty SOUL fails the run before anything is proposed.

import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";

const SOUL_SNAPSHOT_MAX_CHARS = 4000;

/** @returns {{path, text, sha256, chars}} bounded text plus full-file hash and length */
export function readSoulSnapshot(soulPath) {
  if (!soulPath) throw new Error("improve: --soul-path is required");
  const resolved = path.resolve(String(soulPath));
  let full;
  try {
    full = fs.readFileSync(resolved, "utf8");
  } catch (err) {
    throw new Error(`improve: SOUL baseline unavailable at ${resolved} (${err.message}); refusing to propose without the active baseline`);
  }
  if (!full.trim()) {
    throw new Error(`improve: SOUL baseline at ${resolved} is empty; refusing to propose without the active baseline`);
  }
  return {
    path: resolved,
    text: full.slice(0, SOUL_SNAPSHOT_MAX_CHARS),
    sha256: createHash("sha256").update(full, "utf8").digest("hex"),
    chars: full.length,
  };
}
