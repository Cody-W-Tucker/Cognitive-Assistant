// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Consolidation adapted from Backpass src/consolidate.js + src/gap-ledger.js
// (commit 0268201), narrowed to the CA folded ledger: one bounded acpx call
// judges same-gap paraphrases, the merge itself stays mechanical. Failure is
// fail-soft to deterministic lexical identity with a visible run note.

import fs from "node:fs";
import path from "node:path";

import { renderPrompt } from "./prompts.js";
import { persistPrompt, resolveAcpxBin } from "./analyze.js";
import { runAcpxPromptFile } from "./acpx-text.js";
import { modelForRole } from "./models.js";

export const MIN_CONSOLIDATE_ENTRIES = 2;
export const OPEN_GAPS_FILENAME = "open-gaps.json";
function normalizeOpenGapKey(cluster) {
  const raw = String(cluster?.proposedInstruction || cluster?.representativeQuote || cluster?.mistake || cluster?.id || "").toLowerCase().replace(/\s+/g, " ").trim().slice(0, 200);
  return raw || String(cluster?.id || "unknown");
}
export function loadOpenGaps(stateDir) {
  if (!stateDir) return { version: 1, gaps: [] };
  try {
    const raw = fs.readFileSync(path.join(path.resolve(stateDir), OPEN_GAPS_FILENAME), "utf8");
    const parsed = JSON.parse(raw);
    const gaps = Array.isArray(parsed?.gaps) ? parsed.gaps : Array.isArray(parsed) ? parsed : [];
    return { version: 1, gaps };
  } catch {
    return { version: 1, gaps: [] };
  }
}
export function saveOpenGaps(stateDir, gaps) {
  if (!stateDir) return null;
  const resolved = path.resolve(stateDir);
  fs.mkdirSync(resolved, { recursive: true });
  const payload = { version: 1, updatedAt: new Date().toISOString(), gaps: gaps || [] };
  fs.writeFileSync(path.join(resolved, OPEN_GAPS_FILENAME), `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  return path.join(resolved, OPEN_GAPS_FILENAME);
}
/**
 * Mechanically judge/merge all open/singleton observations BEFORE the
 * minGapEvidence eligibility floor. Unions current clusters (including
 * ineligible singletons) with persisted open gaps by stable key/id; when
 * the union reaches the floor the merged cluster becomes eligible and is
 * marked corroboratedOpenGap so the proposal can cite the open-gap merge.
 */
export function corroborateOpenGaps(ledger, persisted, { minGapEvidence = 2 } = {}) {
  const clusters = Array.isArray(ledger?.clusters) ? ledger.clusters.map((c) => ({ ...c })) : [];
  const open = Array.isArray(persisted?.gaps) ? persisted.gaps : [];
  const byId = new Map(open.map((g) => [String(g.id), g]));
  const byKey = new Map(open.map((g) => [String(g.key || normalizeOpenGapKey(g)), g]));
  let corroborated = 0;
  for (const c of clusters) {
    const key = normalizeOpenGapKey(c);
    const match = byId.get(String(c.id)) || byKey.get(key);
    if (!match) continue;
    const before = [...(c.sources || []).map(String)].sort();
    const union = [...new Set([...before, ...((match.sources || []).map(String))])].sort();
    // Cross-run corroboration: a persisted match at/above the floor still
    // marks the eligible cluster as open-gap corroborated on later runs even
    // when this run adds no new distinct sessions. Growth promotes
    // singletons; identity still corroborates eligible repeats.
    if (union.length <= before.length) {
      if (union.length >= minGapEvidence) {
        const was = Boolean(c.corroboratedOpenGap);
        c.sources = union;
        c.count = union.length;
        c.eligible = true;
        c.corroboratedOpenGap = true;
        if (!was) corroborated += 1;
      }
      continue;
    }
    if (union.length >= minGapEvidence) {
      const wasEligible = Boolean(c.eligible);
      c.sources = union;
      c.count = union.length;
      c.eligible = true;
      c.corroboratedOpenGap = true;
      if (!wasEligible) c.openGapPromotedSingleton = true;
      corroborated += 1;
    } else if (!c.eligible) {
      c.sources = union;
      c.count = union.length;
      c.eligible = union.length >= minGapEvidence;
    }
  }
  // Persistable snapshot: union of persisted + current (mechanical, no drop).
  const snapshot = new Map();
  for (const g of open) snapshot.set(String(g.id || g.key), { ...g });
  for (const c of clusters) {
    const snap = {
      id: String(c.id),
      key: normalizeOpenGapKey(c),
      proposedInstruction: c.proposedInstruction,
      representativeQuote: c.representativeQuote,
      mistake: c.mistake,
      sources: [...(c.sources || []).map(String)],
      count: (c.sources || []).length,
      eligible: Boolean(c.eligible),
    };
    snapshot.set(String(c.id), snap);
  }
  return { clusters, corroborated, snapshot: [...snapshot.values()] };
}

function firstMistake(cluster) {
  const flat = String(cluster.mistake || "").replace(/\s+/g, " ").trim();
  if (flat) return flat.length > 160 ? `${flat.slice(0, 160)}...` : flat;
  return "";
}

/** Render folded clusters for the {{GAP_ENTRIES}} slot. */
export function renderGapEntries(clusters) {
  return (clusters || [])
    .map((c) => {
      const sessions = Array.isArray(c.sources) ? c.sources.length : c.count || 0;
      const mistake = firstMistake(c);
      return (
        `[${c.id}] (sessions=${sessions}) ${c.proposedInstruction}` +
        (mistake ? `\n    mistake: ${mistake}` : "")
      );
    })
    .join("\n");
}

/** Render the consolidation model prompt (sentinel FIRST via the loader). */
export function buildConsolidatePrompt(ledger, { promptsDir } = {}) {
  const clusters = ledger?.clusters || [];
  return renderPrompt("consolidate", { GAP_ENTRIES: renderGapEntries(clusters) || "(none)" }, { promptsDir });
}

/**
 * Validate a raw consolidate answer against the folded ledger.
 * Every exact cluster ID presented in the prompt can merge (eligibility is
 * gated after consolidation, so open/singleton IDs are valid merge members).
 * Keeps groups with >=2 distinct presented IDs and unique membership; drops
 * malformed groups, unknown IDs, singletons, and repeat claims.
 */
export function parseConsolidateResult(parsed, ledger) {
  const known = new Set((ledger?.clusters || []).map((c) => String(c?.id)));
  if (!parsed || typeof parsed !== "object" || !Array.isArray(parsed.merges)) return [];
  const claimed = new Set();
  const out = [];
  for (const group of parsed.merges) {
    if (!Array.isArray(group)) continue;
    const ids = [];
    for (const raw of group) {
      if (typeof raw !== "string") continue;
      const id = raw.trim();
      if (!id || !known.has(id)) continue;
      if (claimed.has(id) || ids.includes(id)) continue;
      ids.push(id);
    }
    if (ids.length < 2) continue;
    for (const id of ids) claimed.add(id);
    out.push(ids);
  }
  return out;
}

/**
 * Mechanically merge validated groups. Unions distinct session sources
 * (never double-counts), preserves every per-source quote sighting
 * (first-wins perSource plus a quoteProvenance list so same-source
 * different quotes all survive), keeps one member's instruction, quote,
 * and mistake together as the coherent canonical triple, and re-checks
 * the evidence floor.
 */
export function mergeClusters(ledger, groups, { minGapEvidence = 2 } = {}) {
  const byId = new Map((ledger?.clusters || []).map((c) => [String(c.id), c]));
  const absorbed = new Set();
  const mergedClusters = [];

  // Index groups by membership for O(1) lookup of each cluster's group.
  const groupOf = new Map();
  for (const group of groups || []) {
    for (const id of group) groupOf.set(String(id), group);
  }

  for (const c of ledger?.clusters || []) {
    const id = String(c.id);
    if (absorbed.has(id)) continue;
    const group = groupOf.get(id);
    if (!group) {
      mergedClusters.push(c);
      continue;
    }
    // Only the first member of each group builds the merged cluster.
    if (group[0] !== id) continue;
    const members = group.map((gid) => byId.get(String(gid))).filter(Boolean);
    for (const gid of group) absorbed.add(String(gid));
    const sources = [...new Set(members.flatMap((m) => m.sources || []))].sort();
    // First-wins perSource so no sighting is silently overwritten, plus
    // full variant provenance for same-source different quotes.
    const perSource = {};
    const quoteProvenance = [];
    for (const m of members) {
      for (const [source, sighting] of Object.entries(m.perSource || {})) {
        quoteProvenance.push({
          source: String(source),
          quote: String(sighting?.quote || ""),
          mistake: String(sighting?.mistake || ""),
          from: String(m.id),
        });
        if (!perSource[source]) perSource[source] = { ...sighting };
      }
      for (const entry of m.quoteProvenance || []) {
        quoteProvenance.push({ ...entry });
        if (entry?.source && !perSource[entry.source] && entry.quote) {
          perSource[entry.source] = { quote: entry.quote, mistake: entry.mistake || "" };
        }
      }
    }
    // Coherent canonical triple: instruction, representativeQuote, and
    // mistake all come from the same member (shortest instruction wins).
    const canonical = members.reduce((best, m) =>
      String(m.proposedInstruction || "").length < String(best.proposedInstruction || "").length ? m : best,
    );
    mergedClusters.push({
      ...canonical,
      id: canonical.id,
      proposedInstruction: canonical.proposedInstruction,
      representativeQuote: canonical.representativeQuote,
      mistake: canonical.mistake,
      sources,
      count: sources.length,
      eligible: sources.length >= minGapEvidence,
      perSource,
      quoteProvenance,
      mergedFrom: group.slice(),
    });
  }
  mergedClusters.sort((a, b) => b.count - a.count || String(a.id).localeCompare(String(b.id)));
  return { ...ledger, clusters: mergedClusters };
}

/** Default acpx invoke for consolidation. Same executable protocol as
 * analyze acpx (analyze.js): the `acpx` binary, Pi executor, ACPX
 * text-output (`--format quiet`, never JSON-RPC), extra args from
 * CA_IMPROVE_ACPX_ARGS, persisted prompt via `--file`, role model luna
 * with ACPX --timeout 180s (mandatory, before the agent), model-final
 * JSON extracted strictly from text stdout. */
export function acpxConsolidateInvoke(options = {}) {
  if (options && Object.prototype.hasOwnProperty.call(options, "agent")) {
    throw new Error("CA ACPX executor is fixed to pi (caller agent is not accepted)");
  }
  const { prompt, promptFile = null, model = null, timeoutSec = null, timeoutMs = null, spawnFn = null } = options;
  void prompt;
  void resolveAcpxBin;
  const file = promptFile ? String(promptFile) : "";
  if (!file) {
    return { status: "failed", error: "acpx prompt file is required (reuse persisted prompt)" };
  }
  const out = runAcpxPromptFile({
    role: "consolidate",
    promptFile: file,
    model: model || modelForRole("consolidate"),
    timeoutSec: timeoutSec ?? 180,
    ...(timeoutMs !== null && timeoutMs !== undefined ? { timeoutMs } : {}),
    ...(spawnFn ? { spawnFn } : {}),
  });
  if (out.status !== "ok") {
    return { status: "failed", error: out.error };
  }
  return { status: "ok", result: out.result };
}

/**
 * Run consolidation: acpx-only when >=2 current/open clusters exist.
 * ALL current/open clusters (including ineligible singletons from actual
 * analyzer gap observations) are submitted to the ACPX consolidation prompt
 * BEFORE minGapEvidence eligibility gating; the merge itself can promote
 * distinct-session singletons to eligible. Persists the rendered prompt
 * privately with run/stage metadata. acpx failure/invalid degrades to the
 * deterministic lexical current result with a visible note; it never aborts
 * the run.
 */
export function consolidateLedger(
  ledger,
  { invoke = acpxConsolidateInvoke, promptsDir, stateDir = null, runId = null, minGapEvidence = 2, analyzer = "acpx", persist = true, archivePrompt = null } = {},
) {
  const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
  // Prompt for deferred persistence (resume validates eligibility before any
  // state mutation). Populated below when the judged call is needed.
  let pendingPrompt = null;
  let pendingPromptFile = null;
  let pendingFinalLedger = null;
  // Open/singleton observations are mechanically judged/merged BEFORE the
  // minGapEvidence eligibility floor, then persisted for future runs.
  let working = ledger;
  let openCorroborated = 0;
  let openSnapshot = null;
  try {
    const persisted = loadOpenGaps(stateDir);
    const out = corroborateOpenGaps(ledger, persisted, { minGapEvidence });
    working = { ...ledger, clusters: out.clusters };
    openCorroborated = out.corroborated;
    openSnapshot = out.snapshot;
  } catch {
    working = ledger;
  }
  const persistOpen = (finalLedger) => {
    if (!persist) {
      pendingFinalLedger = finalLedger;
      return;
    }
    try {
      const gaps = (finalLedger?.clusters || []).map((c) => ({
        id: String(c.id),
        key: normalizeOpenGapKey(c),
        proposedInstruction: c.proposedInstruction,
        representativeQuote: c.representativeQuote,
        mistake: c.mistake,
        sources: [...(c.sources || []).map(String)],
        count: (c.sources || []).length,
        eligible: Boolean(c.eligible),
      }));
      const merged = new Map((openSnapshot || []).map((g) => [String(g.id), g]));
      for (const g of gaps) merged.set(String(g.id), g);
      saveOpenGaps(stateDir, [...merged.values()]);
    } catch {
      // persistence best-effort; ledger result still flows downstream
    }
  };
  const clusters = working?.clusters || [];
  const openNote = openCorroborated > 0 ? ` open-gap corroboration merged ${openCorroborated} singleton/eligible gap(s) before the floor.` : "";
  if (clusters.length < MIN_CONSOLIDATE_ENTRIES) {
    persistOpen(working);
    const base = "consolidation skipped: fewer than two open gaps";
    return { ledger: working, skipped: "fewer than two open gaps", merged: openCorroborated, note: `${base}.${openNote}`.trim() };
  }
  if (analyzer === "mock") {
    persistOpen(working);
    const base = "consolidation skipped (mock analyzer): deterministic lexical identity";
    return { ledger: working, skipped: "mock analyzer: deterministic lexical identity", merged: openCorroborated, note: `${base}.${openNote}`.trim() };
  }
  const prompt = buildConsolidatePrompt({ ...working, clusters }, { promptsDir });
  let promptFile = null;
  let persistNote = "";
  const shouldArchivePrompt = archivePrompt ?? persist;
  if (stateDir && shouldArchivePrompt) {
    try {
      promptFile = persistPrompt(path.resolve(stateDir), {
        runId: resolvedRun,
        transcriptId: "consolidate",
        harness: "stage",
        prompt,
        stage: "consolidate",
      });
    } catch (err) {
      // Persistence failure is visible, never silent: consolidation still
      // proceeds, but the run note carries the warning.
      persistNote = `consolidation prompt persistence failed (${err?.message || String(err)}); prompt not archived for this run`;
    }
  }
  const withPersist = (entry) => (persistNote ? { ...entry, note: entry.note ? `${entry.note}\n${persistNote}` : persistNote } : entry);
  if (!promptFile && invoke === acpxConsolidateInvoke) {
    persistOpen(working);
    return withPersist({
      ledger: working,
      failed: "acpx prompt file is required (reuse persisted prompt)",
      merged: 0,
      note: "consolidation failed (acpx prompt file is required (reuse persisted prompt)); continuing with lexical gap identity for this run",
      promptFile,
    });
  }
  let outcome;
  try {
    outcome = invoke({ prompt, promptFile, clusters, promptsDir });
  } catch (err) {
    outcome = { status: "failed", error: err?.message || String(err) };
  }
  if (!outcome || outcome.status !== "ok" || !outcome.result) {
    // Support test doubles returning {status:"ok", merges} directly.
    if (outcome && outcome.status === "ok" && Array.isArray(outcome.merges)) {
      const groups = parseConsolidateResult({ merges: outcome.merges }, working);
      if (!groups.length) {
        persistOpen(working);
        return withPersist({ ledger: working, failed: "no valid merges", merged: 0, note: "consolidation returned no valid merges; continuing with lexical gap identity for this run", promptFile });
      }
      const merged = mergeClusters(working, groups, { minGapEvidence });
      persistOpen(merged);
      return withPersist({ ledger: merged, merged: groups.reduce((n, g) => n + g.length - 1, 0) + openCorroborated, note: `consolidation merged ${groups.length} group(s).${openNote}`.trim(), promptFile });
    }
    persistOpen(working);
    return withPersist({
      ledger: working,
      failed: outcome?.error || "consolidation failed",
      merged: 0,
      note: `consolidation failed (${outcome?.error || "unparseable output"}); continuing with lexical gap identity for this run`,
      promptFile,
    });
  }
  const groups = parseConsolidateResult(outcome.result, working);
  if (!groups.length) {
    persistOpen(working);
    const failed = outcome.result && typeof outcome.result === "object" && Array.isArray(outcome.result.merges) ? false : true;
    return withPersist({
      ledger: working,
      ...(failed ? { failed: "no parseable merge list" } : {}),
      merged: 0,
      note: "consolidation returned no valid merges; continuing with lexical gap identity for this run",
      promptFile,
    });
  }
  const merged = mergeClusters(working, groups, { minGapEvidence });
  persistOpen(merged);
  return withPersist({ ledger: merged, merged: groups.reduce((n, g) => n + g.length - 1, 0) + openCorroborated, note: `consolidation merged ${groups.length} group(s).${openNote}`.trim(), promptFile });
}
