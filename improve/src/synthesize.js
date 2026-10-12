// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Synthesis adapted from Backpass src/synthesize.js + src/proposal.js
// (commit 0268201), narrowed to this slice's contract: produce candidate
// *experience records* only. The SOUL baseline is read-only context —
// synthesis never patches SOUL, memory files, or skills. The apply gate
// owns all writes.

import { createHash } from "node:crypto";

function shortHash(text) {
  return createHash("sha256").update(text).digest("hex").slice(0, 12);
}

function slugify(text) {
  const slug = String(text || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "untitled";
}

/**
 * Render the staged (generated) artifact for one candidate record.
 * Pure function of (record, soulBaseline): the compiler consumes this.
 */
export function renderStagedArtifact(record, soulBaseline = "") {
  const baselineNote = soulBaseline
    ? `Baseline: SOUL.md excerpt (${soulBaseline.length} chars, read-only).`
    : "Baseline: SOUL.md unavailable; record stands alone.";
  return (
    `---\n` +
    `id: ${record.id}\n` +
    `sources: ${record.sources.join(", ")}\n` +
    `---\n\n` +
    `# ${record.title}\n\n` +
    `${record.body}\n\n` +
    `## Evidence\n\n` +
    record.evidence.map((e) => `- (${e.source}) ${e.text}`).join("\n") +
    `\n\n_${baselineNote}_\n`
  );
}

/** Informational diff of the staged artifact against the read-only baseline. */
export function renderDiff(recordId, stagedArtifact) {
  const lines = [`--- SOUL.md (baseline, read-only)`, `+++ staged/${recordId}.md`];
  for (const line of stagedArtifact.split("\n")) lines.push(`+${line}`);
  return lines.join("\n");
}

/**
 * @param {{clusters}} ledger — folded ledger (eligible clusters only become edits)
 * @param {{positiveBySession: Map}} evidenceIndex — sessionId -> positive entries
 * @param {string} soulBaseline — SOUL.md text (read-only context)
 * @returns edits [{id, kind, title, rationale, instructions, evidence, record, stagedArtifact, diff}]
 */
export function synthesizeCandidates(ledger, { evidenceIndex = new Map(), soulBaseline = "" } = {}) {
  const edits = [];
  let index = 0;
  for (const cluster of ledger.clusters || []) {
    if (!cluster.eligible) continue;
    index += 1;
    const recordId = `exp-${slugify(cluster.proposedInstruction).slice(0, 40)}-${shortHash(cluster.id)}`;
    const evidence = cluster.sources.map((source) => {
      const positives = evidenceIndex.get(source) || [];
      const first = positives[0];
      // Per-source quote-backed evidence: never replicate the cluster's
      // first quote/mistake across all sources. Prefer the folded per-source
      // gap sighting, fall back to this source's positive quote.
      const per = (cluster.perSource || {})[source] || {};
      return {
        polarity: "negative",
        text: per.quote || first?.quote || cluster.representativeQuote,
        effect: per.mistake || cluster.mistake,
        moment: first?.effect || "",
        source,
      };
    });
    const record = {
      id: recordId,
      title: cluster.proposedInstruction,
      body: `Recurring gap seen in ${cluster.count} session(s): ${cluster.mistake}`,
      sources: cluster.sources,
      clusterId: cluster.id,
      evidence,
    };
    const stagedArtifact = renderStagedArtifact(record, soulBaseline);
    edits.push({
      id: `e${index}`,
      kind: "add",
      title: `Experience record: ${cluster.proposedInstruction}`,
      rationale: cluster.mistake,
      instructions: [cluster.proposedInstruction],
      evidence,
      record,
      stagedArtifact,
      diff: renderDiff(recordId, stagedArtifact),
    });
  }
  return edits;
}
