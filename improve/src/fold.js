// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Deterministic fold adapted from Backpass src/fold.js (commit 0268201),
// narrowed: cluster near-duplicate gap sightings across sessions, apply the
// minGapEvidence floor, emit a compact folded ledger. No model involved.

import { createHash } from "node:crypto";

import { assertMinGapEvidence } from "./state.js";

function normalizeQuote(text) {
  return String(text ?? "").toLowerCase().replace(/\s+/g, " ").trim().slice(0, 300);
}

function shortHash(text) {
  return createHash("sha256").update(text).digest("hex").slice(0, 12);
}

/**
 * @param {object[]} evidenceRecords — analyzer output (status "ok" entries used)
 * @param {{minGapEvidence?: number}} [options]
 * @returns folded ledger {clusters: [{id, proposedInstruction, representativeQuote, sources, count, eligible, perSource}]}
 */
export function foldEvidence(evidenceRecords, { minGapEvidence = 2 } = {}) {
  minGapEvidence = assertMinGapEvidence(minGapEvidence, "minGapEvidence");
  const usable = (evidenceRecords || []).filter((r) => r && r.status === "ok");
  const groups = new Map();
  for (const record of usable) {
    const sessionId = record.transcriptId;
    for (const gap of record.gaps || []) {
      const key = normalizeQuote(gap.quote || gap.mistake);
      if (!key) continue;
      if (!groups.has(key)) groups.set(key, { gaps: [], sessions: new Set(), perSource: new Map() });
      const group = groups.get(key);
      group.gaps.push(gap);
      group.sessions.add(sessionId);
      // Keep the first gap sighting per source so synthesis can preserve
      // per-source quote-backed evidence instead of replicating one quote.
      if (!group.perSource.has(sessionId)) {
        group.perSource.set(sessionId, {
          quote: String(gap.quote || gap.mistake || key),
          mistake: String(gap.mistake || ""),
        });
      }
    }
  }
  const clusters = [...groups.entries()].map(([key, group]) => {
    const first = group.gaps[0];
    const sources = [...group.sessions].sort();
    return {
      id: `g-${shortHash(key)}`,
      proposedInstruction: String(first.proposedInstruction || "exp-ungrouped"),
      representativeQuote: String(first.quote || first.mistake || key),
      mistake: String(first.mistake || ""),
      sources,
      count: sources.length,
      eligible: sources.length >= minGapEvidence,
      perSource: Object.fromEntries(group.perSource.entries()),
    };
  });
  clusters.sort((a, b) => b.count - a.count || a.id.localeCompare(b.id));
  return { version: 1, minGapEvidence, clusters };
}
