// Private writable copy of the experience-record surface. Synthesis may edit
// only this directory; apply remains the sole writer of the real surface.
import fs from "node:fs";
import path from "node:path";

import { parseWorkspaceFrontmatter } from "./workspace-frontmatter.js";

export { parseWorkspaceFrontmatter };

function safeId(id) {
  const out = String(id || "").replace(/[^a-zA-Z0-9._-]/g, "_");
  return out || "untitled";
}

export function prepareExperienceWorkspace({ stateDir, records = [], runId = null } = {}) {
  if (!stateDir) throw new Error("stateDir is required for an experience workspace");
  const base = path.join(path.resolve(stateDir), "synthesis-workspace");
  let root = base;
  if (runId !== null && runId !== undefined && String(runId).length) {
    const safeRun = String(runId).replace(/[^a-zA-Z0-9._-]/g, "_") || "run";
    root = path.join(base, safeRun);
  }
  fs.rmSync(root, { recursive: true, force: true });
  fs.mkdirSync(root, { recursive: true, mode: 0o700 });
  const originals = new Map();
  for (const record of records) {
    const id = safeId(record?.id);
    const text = String(record?.text || record?.stagedArtifact || "");
    const file = `${id}.md`;
    fs.writeFileSync(path.join(root, file), text, { encoding: "utf8", mode: 0o600 });
    originals.set(file, text);
  }
  return { root, originals: Object.fromEntries(originals) };
}

// Durable-write containment: synthesis must refuse (forbid/deny) any durable
// write to the source repo, SOUL.md, skills, or Hermes. The private
// synthesis-workspace under stateDir is the only writable synthesis target;
// apply remains the sole durable writer of the real experience surface.
export const SYNTHESIS_WORKSPACE_DIRNAME = "synthesis-workspace";
export const FORBIDDEN_SYNTHESIS_TARGETS = ["repo", "SOUL.md", "SOUL", "skills", "Hermes"];
export function isForbiddenSynthesisPath(target) {
  const lowered = String(target || "").toLowerCase();
  return (
    lowered.includes("soul") ||
    lowered.includes("workspaces/skills") ||
    lowered.includes("workspaces/experience") ||
    lowered.includes(".hermes") ||
    lowered.includes("hermes/state.db") ||
    (!lowered.includes(SYNTHESIS_WORKSPACE_DIRNAME) &&
      (lowered.includes("/repo") || lowered.endsWith(".git") || lowered === "repo"))
  );
}
export function assertSynthesisContainment(target) {
  if (isForbiddenSynthesisPath(target)) {
    throw new Error(`synthesis refused: durable writes to repo/SOUL/skills/Hermes are forbidden (target ${JSON.stringify(target)}); write only inside synthesis-workspace`);
  }
}
function anchoredDiff({ id, file, kind, before, text }) {
  const header = [`--- a/${kind === "created" ? "/dev/null" : file} (${id})`, `+++ b/${kind === "deleted" ? "/dev/null" : file} (${id})`];
  const body = [];
  if (kind === "created") {
    for (const line of String(text || "").split("\n")) body.push(`+${line}`);
  } else if (kind === "deleted") {
    for (const line of String(before || "").split("\n")) body.push(`-${line}`);
  } else {
    for (const line of String(before || "").split("\n")) body.push(`-${line}`);
    for (const line of String(text || "").split("\n")) body.push(`+${line}`);
  }
  return [...header, ...body].join("\n");
}
export function measureExperienceWorkspace(workspace) {
  const originals = new Map(Object.entries(workspace?.originals || {}));
  const root = path.resolve(workspace?.root || "");
  const current = new Set(fs.readdirSync(root).filter((name) => name.endsWith(".md")).sort());
  const changes = [];
  for (const file of current) {
    const text = fs.readFileSync(path.join(root, file), "utf8");
    const before = originals.get(file);
    if (before === text) continue;
    const kind = before === undefined ? "created" : "modified";
    const id = `m-${file.slice(0, -3)}`;
    const entry = { id, recordId: file.slice(0, -3), file, path: file, kind, ...(before === undefined ? { text } : { before, text }) };
    entry.diff = anchoredDiff({ id, file, kind, before, text });
    // Provenance comes ONLY from the actual changed file frontmatter.
    // Never auto-assigned, never cyclic: missing/invalid yields no linkage.
    try {
      const parsed = parseWorkspaceFrontmatter(text);
      if (!parsed.parseError && parsed.clusterId && Array.isArray(parsed.provisionalSources) && parsed.provisionalSources.length >= 2) {
        const distinct = [...new Set(parsed.provisionalSources.map((s) => String(s)))];
        entry.clusterId = parsed.clusterId;
        entry.provisionalSources = distinct;
        entry.eligibleSources = distinct;
        entry.sources = distinct;
      }
    } catch {
      // Invalid provenance stays unlinked; measured for individual rejection.
    }
    changes.push(entry);
  }
  for (const [file, before] of originals) {
    if (!current.has(file)) {
      const id = `m-${file.slice(0, -3)}`;
      const entry = { id, recordId: file.slice(0, -3), file, path: file, kind: "deleted", before };
      entry.diff = anchoredDiff({ id, file, kind: "deleted", before, text: "" });
      changes.push(entry);
    }
  }
  changes.sort((a, b) => String(a.id).localeCompare(String(b.id)));
  return changes;
}
