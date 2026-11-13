// The tail both entry points share: from a folded ledger to a written
// proposal. `run` reaches it after discovery and analysis, `synthesize`
// after reloading saved evidence; everything past the ledger is identical.

import { annotate } from "./annotate.js";
import { synthesize } from "./synthesize.js";
import { readRejections, timestampId, writeProposal } from "./state.js";

/**
 * A rejected identity (cluster id or title) stays suppressed unless the record
 * now cites more sessions or a session the rejection did not. Rejection rows
 * without an identity or sources never suppress.
 */
function isSuppressedByRejection(record, rejections) {
  const cluster = String(record.clusterId || "").trim();
  const title = String(record.title || "").trim();
  const sources = new Set((record.sources || []).map(String));
  return rejections.some((r) => {
    const key = String(r?.clusterId || "").trim() || String(r?.title || "").trim();
    if (!key || (key !== cluster && key !== title)) return false;
    const rejected = Array.isArray(r.sources) ? [...new Set(r.sources.map(String).filter(Boolean))] : [];
    if (!rejected.length) return false;
    return sources.size <= rejected.length && [...sources].every((s) => rejected.includes(s));
  });
}

function toEdit({ plan, annotation, record }, cluster) {
  const corroborated = Boolean(cluster?.corroboratedOpenGap);
  const base = annotation.reason || record.body;
  const rationale = corroborated && !/open-gap|singleton/i.test(base) ? `open-gap corroborated singleton: ${base}` : base;
  return {
    id: plan.id,
    kind: "add",
    title: String(record.title).startsWith("Experience record:") ? String(record.title) : `Experience record: ${record.title}`,
    rationale,
    evidence: record.evidence,
    record,
    annotation: { verdict: "keep", reason: rationale },
    clusterId: record.clusterId,
    ...(corroborated ? { corroboratedOpenGap: true } : {}),
  };
}

/**
 * Synthesize plans over `ledger`, annotate them, drop rejected identities,
 * and write the proposal. Model failures become notes on an edit-less
 * proposal rather than errors.
 */
export async function propose({
  stateDir,
  runId,
  ledger,
  evidenceRecords,
  soul,
  floor,
  invoke,
  analyzer,
  consolidation,
  stats,
  harnessSummary,
  emit,
  extra = {},
}) {
  const evidenceIndex = new Map(evidenceRecords.map((r) => [r.transcriptId, r.positive || []]));
  const rejections = readRejections(stateDir);
  emit("synthesize:start");
  const synthesis = await synthesize(ledger, {
    invoke,
    stateDir,
    runId,
    floor,
    soul,
    evidenceIndex,
    rejections,
    transcriptCount: stats.transcripts,
    harnessSummary,
    runNote: consolidation.note,
  });
  const annotation = synthesis.plans.length
    ? await annotate(synthesis.plans, { invoke, stateDir, runId, ledger, evidenceIndex, soul })
    : { kept: [], annotated: 0, failed: false, note: "" };
  const clusters = new Map(ledger.clusters.map((c) => [String(c.id), c]));
  const edits = annotation.kept
    .filter(({ record }) => !isSuppressedByRejection(record, rejections))
    .map((kept) => toEdit(kept, clusters.get(String(kept.record.clusterId))));
  const now = new Date();
  const proposal = {
    version: 1,
    id: timestampId("prop", now),
    createdAt: now.toISOString(),
    reviewed: false,
    appliedAt: null,
    scope: "global",
    ...extra,
    minGapEvidence: floor,
    soul: { path: soul.path, sha256: soul.sha256, chars: soul.chars },
    edits,
    notes: [consolidation.note, synthesis.note, annotation.note].filter(Boolean),
    consolidation: {
      skipped: Boolean(consolidation.skipped),
      failed: Boolean(consolidation.failed),
      merged: consolidation.merged || 0,
      note: consolidation.note || "",
    },
    synthesis: { analyzer, failed: synthesis.failed, plans: synthesis.plans.length, note: synthesis.note },
    annotation: { annotated: annotation.annotated, failed: annotation.failed, note: annotation.note },
    stats: { ...stats, clusters: ledger.clusters.length, eligible: ledger.clusters.filter((c) => c.eligible).length },
  };
  writeProposal(stateDir, proposal);
  emit("synthesize:done", { plans: synthesis.plans.length, annotated: annotation.annotated, edits: edits.length, note: annotation.note || synthesis.note });
  return proposal;
}
