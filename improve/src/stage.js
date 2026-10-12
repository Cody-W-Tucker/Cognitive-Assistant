// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// CA-native private staging: synth output is a staged change plan, never the
// final authoritative proposal. Staging is deterministic under stateDir and
// terminal review/apply consumes only buildFinalProposal output (annotated).

import fs from "node:fs";
import path from "node:path";

import { validateCandidate } from "./synthesize.js";

function stagingDir(stateDir) {
  return path.join(path.resolve(stateDir), "staging");
}

function ensureStaging(stateDir) {
  if (!stateDir) return null;
  const dir = stagingDir(stateDir);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

/**
 * Deterministically stage synth candidates as a change plan.
 * Preserves input order and stable ids (assigns e<N> only when missing).
 * Persists machine-readable staging metadata privately (never the repo).
 *
 * @returns staged array (same objects, shallow-copied)
 */
export function stageCandidates(candidates, { stateDir = null, runId = null } = {}) {
  const list = Array.isArray(candidates) ? candidates : [];
  const staged = list.map((c, i) => {
    const copy = { ...(c || {}) };
    if (!copy.id) copy.id = `e${i + 1}`;
    return copy;
  });
  if (stateDir) {
    const dir = ensureStaging(stateDir);
    const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
    fs.writeFileSync(
      path.join(dir, "candidates.json"),
      `${JSON.stringify(staged, null, 2)}\n`,
      "utf8",
    );
    fs.writeFileSync(
      path.join(dir, "stage.json"),
      `${JSON.stringify(
        {
          version: 1,
          runId: String(resolvedRun),
          count: staged.length,
          ids: staged.map((c) => String(c.id)),
          createdAt: new Date().toISOString(),
        },
        null,
        2,
      )}\n`,
      "utf8",
    );
  }
  return staged;
}

/**
 * Strict staged validation: structural kind/title/body/rationale/compiler
 * fields plus exact quote+session binding (delegates to synthesize's
 * validateCandidate so the floor cannot be met with swapped/global quotes).
 */
export function validateStaged(candidate, { ledger, evidenceIndex = new Map() } = {}) {
  const errors = [];
  if (!candidate || typeof candidate !== "object") return { ok: false, errors: ["staged candidate is required"] };
  if (candidate.kind !== "add") errors.push(`kind must be "add" (got ${JSON.stringify(candidate.kind)})`);
  const title = candidate.title || candidate.record?.title;
  if (!title || !String(title).trim()) errors.push("title is required");
  const check = validateCandidate(candidate, { ledger, evidenceIndex });
  for (const e of check.errors || []) errors.push(e);
  // Rationale may live top-level (synth edits) or be implied by record.body;
  // require at least one of them so staged plans stay reviewable.
  const rationale = candidate.rationale || candidate.record?.body;
  if (!rationale || !String(rationale).trim()) errors.push("rationale/body is required");
  return { ok: errors.length === 0, errors };
}

function readMeasurements(stateDir) {
  try {
    const raw = fs.readFileSync(path.join(stagingDir(stateDir), "measurements.json"), "utf8");
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

/**
 * Build the terminal final proposal from staged candidates only.
 * Throws when any non-reverted candidate lacks a final annotation —
 * unannotated staging can never reach apply/final proposal.
 * Measurement coverage (when measurements exist) requires each
 * non-reverted candidate to have a measurement carrying annotation or
 * explicit revert. Returns the kept finalists (reverted/dropped excluded).
 */
export function buildFinalProposal(staged, { stateDir = null } = {}) {
  const list = Array.isArray(staged) ? staged : [];
  const measurements = stateDir ? readMeasurements(stateDir) : null;
  const byCandidate = new Map((measurements || []).map((m) => [String(m.candidateId || m.id), m]));
  for (const c of list) {
    const id = String(c?.id || "unknown");
    if (c?.reverted === true) continue;
    if (!c?.annotation) {
      throw new Error(`candidate ${id} has no final annotation; staged candidates cannot reach final proposal without annotate`);
    }
    if (!c.annotation.verdict || !String(c.annotation.verdict).trim()) {
      throw new Error(`candidate ${id} annotation verdict is required`);
    }
    if (c.kind !== "add") throw new Error(`candidate ${id} kind must be "add"`);
    const record = c.record || {};
    if (!record.title || !String(record.title).trim()) throw new Error(`candidate ${id} record.title is required`);
    if (!record.body || !String(record.body).trim()) throw new Error(`candidate ${id} record.body is required`);
    if (!record.counterevidence || !String(record.counterevidence).trim()) {
      throw new Error(`candidate ${id} record.counterevidence is required`);
    }
    if (!record.compilerImplication || !String(record.compilerImplication).trim()) {
      throw new Error(`candidate ${id} record.compilerImplication is required`);
    }
    if (measurements) {
      const m = byCandidate.get(id) || byCandidate.get(String(`m-${id}`));
      if (!m || (!m.annotation && m.reverted !== true)) {
        throw new Error(`candidate ${id} has no measurement annotation or explicit revert`);
      }
    }
  }
  return list.filter((c) => c?.reverted !== true && c?.annotation?.verdict === "keep");
}
