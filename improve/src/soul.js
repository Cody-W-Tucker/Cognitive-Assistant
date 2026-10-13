// Required active-SOUL contextualization for the CA improvement pass.
//
// The canonical SOUL baseline resolves to the repo-root
// workspaces/alignment/artifacts/SOUL.md independently of CWD; an explicit
// --soul-path overrides it. Snapshots are read-only: missing, unreadable, or
// empty SOUL fails closed before synthesis/annotation/proposal. Callers
// receive bounded snapshot text plus a stable sha256 over the full file.

import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";

export const SOUL_SNAPSHOT_MAX_CHARS = 4000;
export const SOUL_RELATIVE_PATH = path.join(
  "workspaces",
  "alignment",
  "artifacts",
  "SOUL.md",
);

/** Repo root resolved relative to the runtime, never CWD. */
export function defaultRepoRoot() {
  return path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "..",
    "..",
  );
}

/** Canonical default SOUL path, independent of CWD. */
export function defaultSoulPath() {
  return path.join(defaultRepoRoot(), SOUL_RELATIVE_PATH);
}

/** Explicit path wins; absent flag resolves to the canonical default. */
export function resolveSoulPath(explicit) {
  if (explicit !== null && explicit !== undefined && String(explicit).trim() !== "") {
    return path.resolve(String(explicit));
  }
  return defaultSoulPath();
}

/**
 * Read the SOUL snapshot (read-only). Fails closed when the file is
 * missing, unreadable, or empty/whitespace-only.
 *
 * @returns {{path, text, sha256, chars}} bounded text + full-file hash/chars
 */
export function readSoulSnapshot(explicit) {
  const resolved = resolveSoulPath(explicit);
  let full;
  try {
    full = fs.readFileSync(resolved, "utf8");
  } catch (err) {
    throw new Error(
      `improve: SOUL baseline unavailable at ${resolved} (${err?.message || err}); ` +
        `refusing synthesis/annotation/proposal without the active baseline`,
    );
  }
  if (!full || !full.trim()) {
    throw new Error(
      `improve: SOUL baseline at ${resolved} is empty; ` +
        `refusing synthesis/annotation/proposal without the active baseline`,
    );
  }
  return {
    path: resolved,
    text: full.slice(0, SOUL_SNAPSHOT_MAX_CHARS),
    sha256: createHash("sha256").update(full, "utf8").digest("hex"),
    chars: full.length,
  };
}
