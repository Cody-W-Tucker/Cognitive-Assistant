// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Consolidation adapted from Backpass src/consolidate.js + src/gap-ledger.js
// (commit 0268201), narrowed to the CA folded ledger: one bounded model call
// judges same-gap paraphrases, the merge itself stays mechanical. A failed or
// invalid judgment falls back to exact observation identity with a run note.
//
// Open gaps persist across runs in <stateDir>/open-gaps.json so a gap seen
// once per run can still reach the evidence floor. They match only on the
// normalized observation text or on model-validated merge membership, never
// on instruction text: one generic instruction across unrelated quotes must
// not corroborate.

import path from "node:path";

import { renderPrompt } from "./prompts.js";
import { assertMinGapEvidence, normalizeQuote, persistPrompt, readJson, writeJson } from "./state.js";

const OPEN_GAPS_FILENAME = "open-gaps.json";

const observationKey = (cluster) => normalizeQuote(cluster?.representativeQuote || cluster?.mistake || "");

export function loadOpenGaps(stateDir) {
  const parsed = readJson(path.join(stateDir, OPEN_GAPS_FILENAME));
  return { version: 1, gaps: Array.isArray(parsed?.gaps) ? parsed.gaps : [] };
}

export function saveOpenGaps(stateDir, gaps) {
  writeJson(path.join(stateDir, OPEN_GAPS_FILENAME), { version: 1, updatedAt: new Date().toISOString(), gaps });
}

/** Persistable form of one cluster, carrying the identities later runs match on. */
function openGapEntry(c) {
  const key = observationKey(c);
  const memberKeys = new Set((c.memberKeys || []).map(String));
  if (key) memberKeys.add(key);
  for (const entry of c.quoteProvenance || []) {
    const quoteKey = normalizeQuote(entry?.quote);
    if (quoteKey) memberKeys.add(quoteKey);
  }
  return {
    id: String(c.id),
    key,
    proposedInstruction: c.proposedInstruction,
    representativeQuote: c.representativeQuote,
    mistake: c.mistake,
    sources: (c.sources || []).map(String),
    count: (c.sources || []).length,
    eligible: Boolean(c.eligible),
    ...(c.mergedFrom ? { mergedFrom: [...c.mergedFrom] } : {}),
    memberIds: (c.mergedFrom || c.memberIds || [String(c.id)]).map(String),
    memberKeys: [...memberKeys].filter(Boolean),
    ...(c.perSource ? { perSource: { ...c.perSource } } : {}),
    ...(c.quoteProvenance ? { quoteProvenance: c.quoteProvenance.map((e) => ({ ...e })) } : {}),
  };
}

/**
 * Fold one member's per-source sightings into (perSource, quoteProvenance):
 * first sighting per source wins, every quote variant stays in provenance.
 */
function absorbProvenance(perSource, quoteProvenance, member) {
  for (const [source, sighting] of Object.entries(member.perSource || {})) {
    quoteProvenance.push({ source: String(source), quote: String(sighting?.quote || ""), mistake: String(sighting?.mistake || ""), from: String(member.id) });
    if (!perSource[source]) perSource[source] = { ...sighting };
  }
  for (const entry of member.quoteProvenance || []) {
    quoteProvenance.push({ ...entry });
    if (entry?.source && !perSource[entry.source] && entry.quote) {
      perSource[entry.source] = { quote: entry.quote, mistake: entry.mistake || "" };
    }
  }
}

/**
 * Corroborate current clusters against persisted open gaps before the
 * evidence floor: a match unions distinct sessions and provenance. A cluster
 * that reaches the floor this way is marked `corroboratedOpenGap` (and
 * `openGapPromotedSingleton` when it was not eligible on its own).
 */
export function corroborateOpenGaps(ledger, persisted, { minGapEvidence = 2 } = {}) {
  const floor = assertMinGapEvidence(minGapEvidence, "minGapEvidence");
  const clusters = (ledger?.clusters || []).map((c) => ({ ...c, sources: (c.sources || []).map(String) }));
  const open = Array.isArray(persisted?.gaps) ? persisted.gaps : [];
  const byId = new Map(open.map((g) => [String(g.id), g]));
  const byKey = new Map();
  const byMemberId = new Map();
  const byMemberKey = new Map();
  for (const g of open) {
    const key = String(g.key || observationKey(g));
    if (key) byKey.set(key, g);
    for (const id of g.mergedFrom || g.memberIds || []) byMemberId.set(String(id), g);
    for (const memberKey of g.memberKeys || []) {
      const normalized = normalizeQuote(memberKey);
      if (normalized) byMemberKey.set(normalized, g);
    }
    const sightings = [...(g.quoteProvenance || []), ...Object.values(g.perSource || {})];
    for (const sighting of sightings) {
      const normalized = normalizeQuote(sighting?.quote);
      if (normalized && !byMemberKey.has(normalized)) byMemberKey.set(normalized, g);
    }
  }
  const findMatch = (c) => {
    const key = observationKey(c);
    const direct = byId.get(String(c.id));
    // Same id with different observation text is a different gap.
    if (direct && key === String(direct.key || observationKey(direct))) return direct;
    if (key && byKey.has(key)) return byKey.get(key);
    if (byMemberId.has(String(c.id))) return byMemberId.get(String(c.id));
    if (key && byMemberKey.has(key)) return byMemberKey.get(key);
    return null;
  };
  let corroborated = 0;
  for (const c of clusters) {
    const match = findMatch(c);
    if (!match) continue;
    const union = [...new Set([...c.sources, ...(match.sources || []).map(String)])].sort();
    const grew = union.length > c.sources.length;
    if (union.length < floor && !(grew && !c.eligible)) continue;
    const perSource = { ...(c.perSource || {}) };
    const quoteProvenance = [...(c.quoteProvenance || [])];
    absorbProvenance(perSource, quoteProvenance, match);
    if (union.length >= floor) {
      if (grew && !c.eligible) c.openGapPromotedSingleton = true;
      if (grew || !c.corroboratedOpenGap) corroborated += 1;
      c.corroboratedOpenGap = true;
    }
    c.sources = union;
    c.count = union.length;
    c.eligible = union.length >= floor;
    if (Object.keys(perSource).length) c.perSource = perSource;
    if (quoteProvenance.length) c.quoteProvenance = quoteProvenance;
  }
  return { clusters, corroborated };
}

function renderGapEntries(clusters) {
  return (clusters || [])
    .map((c) => {
      const flat = String(c.mistake || "").replace(/\s+/g, " ").trim();
      const mistake = flat.length > 160 ? `${flat.slice(0, 160)}...` : flat;
      return `[${c.id}] (sessions=${(c.sources || []).length}) ${c.proposedInstruction}` + (mistake ? `\n    mistake: ${mistake}` : "");
    })
    .join("\n");
}

function buildConsolidatePrompt(ledger) {
  return renderPrompt("consolidate", { GAP_ENTRIES: renderGapEntries(ledger?.clusters) || "(none)" });
}

/**
 * Validate merge groups against every cluster id shown to the model
 * (singletons included). Keeps groups of >=2 distinct known ids with unique
 * membership; drops malformed groups, unknown ids, and repeat claims.
 */
export function parseConsolidateResult(parsed, ledger) {
  const known = new Set((ledger?.clusters || []).map((c) => String(c?.id)));
  if (!Array.isArray(parsed?.merges)) return [];
  const claimed = new Set();
  const out = [];
  for (const group of parsed.merges) {
    if (!Array.isArray(group)) continue;
    const ids = [];
    for (const raw of group) {
      const id = typeof raw === "string" ? raw.trim() : "";
      if (id && known.has(id) && !claimed.has(id) && !ids.includes(id)) ids.push(id);
    }
    if (ids.length < 2) continue;
    for (const id of ids) claimed.add(id);
    out.push(ids);
  }
  return out;
}

/**
 * Mechanically merge validated groups: union distinct sessions, keep every
 * per-source sighting, take instruction/quote/mistake together from one member
 * (shortest instruction), and re-check the evidence floor.
 */
export function mergeClusters(ledger, groups, { minGapEvidence = 2 } = {}) {
  const floor = assertMinGapEvidence(minGapEvidence, "minGapEvidence");
  const byId = new Map((ledger?.clusters || []).map((c) => [String(c.id), c]));
  const groupOf = new Map();
  for (const group of groups || []) for (const id of group) groupOf.set(String(id), group);
  const out = [];
  for (const c of ledger?.clusters || []) {
    const group = groupOf.get(String(c.id));
    if (!group) {
      out.push(c);
      continue;
    }
    if (group[0] !== String(c.id)) continue;
    const members = group.map((id) => byId.get(String(id))).filter(Boolean);
    const sources = [...new Set(members.flatMap((m) => m.sources || []))].sort();
    const perSource = {};
    const quoteProvenance = [];
    for (const m of members) absorbProvenance(perSource, quoteProvenance, m);
    const canonical = members.reduce((best, m) =>
      String(m.proposedInstruction || "").length < String(best.proposedInstruction || "").length ? m : best,
    );
    out.push({
      ...canonical,
      sources,
      count: sources.length,
      eligible: sources.length >= floor,
      perSource,
      quoteProvenance,
      mergedFrom: group.slice(),
      memberIds: group.slice(),
      memberKeys: [...new Set(members.map(observationKey).filter(Boolean))],
    });
  }
  out.sort((a, b) => b.count - a.count || String(a.id).localeCompare(String(b.id)));
  return { ...ledger, clusters: out };
}

/**
 * Corroborate against open gaps, then (with >=2 clusters) ask the model which
 * clusters are the same gap and merge them. Never throws on a model failure.
 *
 * @returns {{ledger, openGaps, merged, note, skipped?, failed?}} `openGaps` is
 *   the snapshot the caller saves with saveOpenGaps once it accepts the result.
 */
export async function consolidateLedger(ledger, { invoke, stateDir, runId, minGapEvidence = 2 }) {
  const floor = assertMinGapEvidence(minGapEvidence, "minGapEvidence");
  const persisted = loadOpenGaps(stateDir);
  const { clusters, corroborated } = corroborateOpenGaps(ledger, persisted, { minGapEvidence: floor });
  const working = { ...ledger, clusters };
  const openNote = corroborated ? ` open-gap corroboration merged ${corroborated} singleton/eligible gap(s) before the floor.` : "";
  const finish = (final, merged, note, extra = {}) => {
    const snapshot = new Map(persisted.gaps.map((g) => [String(g.id || g.key), { ...g }]));
    for (const c of [...clusters, ...final.clusters]) snapshot.set(String(c.id), openGapEntry(c));
    return { ledger: final, openGaps: [...snapshot.values()], merged, note: `${note}${openNote}`.trim(), ...extra };
  };
  if (clusters.length < 2) {
    return finish(working, corroborated, "consolidation skipped: fewer than two open gaps.", { skipped: "fewer than two open gaps" });
  }
  let reply;
  try {
    const prompt = buildConsolidatePrompt(working);
    persistPrompt(stateDir, { runId, name: "consolidate", prompt, meta: { stage: "consolidate" } });
    reply = await invoke("consolidate", prompt, { ledger: working });
  } catch (err) {
    return finish(working, 0, `consolidation failed (${err.message}); continuing with exact observation identity for this run.`, { failed: err.message });
  }
  if (!Array.isArray(reply?.merges)) {
    return finish(working, 0, "consolidation returned no parseable merge list; continuing with exact observation identity for this run.", { failed: "no parseable merge list" });
  }
  const groups = parseConsolidateResult(reply, working);
  if (!groups.length) {
    return finish(working, 0, "consolidation returned no valid merges; continuing with exact observation identity for this run.");
  }
  const mergedLedger = mergeClusters(working, groups, { minGapEvidence: floor });
  const mergedCount = groups.reduce((n, g) => n + g.length - 1, 0) + corroborated;
  return finish(mergedLedger, mergedCount, `consolidation merged ${groups.length} group(s).`);
}
