// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// CA-native private staging: synth output is a staged change plan, never the
// final authoritative proposal. Staging is deterministic under stateDir and
// terminal review/apply consumes only buildFinalProposal output (annotated).

import fs from "node:fs";
import path from "node:path";

import { validateCandidate, validateChangePlan, renderStagedArtifact, renderDiff } from "./synthesize.js";

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
 * Deterministically stage narrow synth change plans.
 * Strips any authoritative final fields if present so a synth final
 * record can never flow through: only id/kind/clusterId/
 * provisionalIntent/provisionalSources/provisionalCount survive.
 * Preserves input order and stable ids (assigns e<N> only when missing).
 * Persists machine-readable staging metadata privately (never the repo).
 *
 * @returns staged array (narrow plans only)
 */
export function stageCandidates(candidates, { stateDir = null, runId = null } = {}) {
  const list = Array.isArray(candidates) ? candidates : [];
  const staged = list.map((c, i) => {
    const copy = {};
    copy.id = c?.id || `e${i + 1}`;
    copy.kind = "add";
    if (c?.clusterId !== undefined) copy.clusterId = c.clusterId;
    const intent = c?.provisionalIntent ?? c?.intent;
    if (intent !== undefined) copy.provisionalIntent = intent;
    if (c?.provisionalSources !== undefined) copy.provisionalSources = c.provisionalSources;
    else if (c?.sources !== undefined) copy.provisionalSources = c.sources;
    if (c?.provisionalCount !== undefined) copy.provisionalCount = c.provisionalCount;
    if (c?.reverted === true) copy.reverted = true;
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
 * Strict staged validation: narrow plans only. Delegates to synth's
 * validateChangePlan so the floor is cluster linkage + provisional intent/
 * context. Any authoritative final field on the plan fails.
 */
export function validateStaged(candidate, { ledger, evidenceIndex = new Map() } = {}) {
  void evidenceIndex;
  const check = validateChangePlan(candidate, { ledger });
  const errors = [...(check.errors || [])];
  if (!candidate || typeof candidate !== "object") return { ok: false, errors: ["staged change plan is required"] };
  if (candidate.kind !== "add") errors.push(`kind must be "add" (got ${JSON.stringify(candidate.kind)})`);
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
 * Build the terminal final proposal from ANNOTATED finals only.
 * Throws when any non-reverted plan lacks a final annotation —
 * unannotated staging can never reach apply/final proposal.
 * For verdict keep, the annotation must carry the complete durable
 * record (title/body/clusterId/sources/evidence/counterevidence/
 * compilerImplication/rationale); the record is mechanically validated
 * (exact session-bound quotes) and the staged artifact/diff are rendered
 * here from that final record. Synth plans contribute no record/evidence.
 * Measurement coverage (when measurements exist) requires each
 * non-reverted plan to have a measurement carrying annotation or
 * explicit revert. Returns the kept finalists (reverted/dropped
 * excluded) as full edits for proposal/apply.
 */
export function buildFinalProposal(staged, { stateDir = null, ledger = null, evidenceIndex = new Map(), soulBaseline = "" } = {}) {
  const list = Array.isArray(staged) ? staged : [];
  const measurements = stateDir ? readMeasurements(stateDir) : null;
  const byCandidate = new Map((measurements || []).map((m) => [String(m.candidateId || m.id), m]));
  const finals = [];
  for (const c of list) {
    const id = String(c?.id || "unknown");
    if (c?.reverted === true) continue;
    if (!c?.annotation) {
      throw new Error(`candidate ${id} has no final annotation; staged change plans cannot reach final proposal without annotate`);
    }
    if (!c.annotation.verdict || !String(c.annotation.verdict).trim()) {
      throw new Error(`candidate ${id} annotation verdict is required`);
    }
    const verdict = String(c.annotation.verdict).trim();
    if (verdict !== "keep" && verdict !== "drop" && verdict !== "revert") {
      throw new Error(`candidate ${id} annotation verdict must be keep|drop|revert`);
    }
    if (c.kind !== "add") throw new Error(`candidate ${id} kind must be "add"`);
    if (verdict !== "keep") continue;
    const record = c.annotation.record || c.finalRecord || c.record;
    if (!record || typeof record !== "object") {
      throw new Error(`candidate ${id} keep requires an annotation final record; synth plans carry no record`);
    }
    // No inherited synth record: the staged plan must not carry one.
    if (c.record !== undefined || c.evidence !== undefined || c.title !== undefined) {
      throw new Error(`candidate ${id} carries a synth final record; annotation is the sole full-record origin`);
    }
    if (ledger) {
      const idx = evidenceIndex instanceof Map ? evidenceIndex : new Map();
      const check = validateCandidate({ record, evidence: record.evidence }, { ledger, evidenceIndex: idx });
      if (!check.ok) {
        throw new Error(`candidate ${id} annotation final record invalid (${(check.errors || []).join("; ") || "validation failed"})`);
      }
    } else {
      if (!record.title || !String(record.title).trim()) throw new Error(`candidate ${id} record.title is required`);
      if (!record.body || !String(record.body).trim()) throw new Error(`candidate ${id} record.body is required`);
      if (!record.counterevidence || !String(record.counterevidence).trim()) {
        throw new Error(`candidate ${id} record.counterevidence is required`);
      }
      if (!record.compilerImplication || !String(record.compilerImplication).trim()) {
        throw new Error(`candidate ${id} record.compilerImplication is required`);
      }
    }
    if (measurements) {
      const m = byCandidate.get(id) || byCandidate.get(String(`m-${id}`));
      if (!m || (!m.annotation && m.reverted !== true)) {
        throw new Error(`candidate ${id} has no measurement annotation or explicit revert`);
      }
    }
    const finalRecord = { ...record };
    const stagedArtifact = renderStagedArtifact(finalRecord, soulBaseline);
    const rationale = c.annotation.reason || c.annotation.rationale || finalRecord.body || "";
    finals.push({
      id,
      kind: "add",
      title: finalRecord.title?.startsWith("Experience record:") ? finalRecord.title : `Experience record: ${finalRecord.title}`,
      rationale,
      instructions: Array.isArray(c.annotation.instructions) && c.annotation.instructions.length ? c.annotation.instructions : [finalRecord.title],
      evidence: finalRecord.evidence,
      record: finalRecord,
      counterevidence: finalRecord.counterevidence,
      compilerImplication: finalRecord.compilerImplication,
      stagedArtifact,
      diff: renderDiff(finalRecord.id || id, stagedArtifact),
      annotation: { verdict: "keep", reason: rationale },
      clusterId: finalRecord.clusterId,
    });
  }
  return finals;
}
