// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Consolidation adapted from Backpass src/consolidate.js + src/gap-ledger.js
// (commit 0268201), narrowed to the CA folded ledger: one bounded acpx call
// judges same-gap paraphrases, the merge itself stays mechanical. Failure is
// fail-soft to deterministic lexical identity with a visible run note.

import { spawnSync } from "node:child_process";
import path from "node:path";

import { renderPrompt } from "./prompts.js";
import { persistPrompt, resolveAcpxBin } from "./analyze.js";
import { buildAcpxArgs, extractAcpxFinalJson } from "./acpx-text.js";
import { modelForRole } from "./models.js";

export const MIN_CONSOLIDATE_ENTRIES = 2;

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
 * Only eligible/open cluster IDs — the exact set presented in the prompt —
 * can merge. Keeps groups with >=2 distinct eligible IDs and unique
 * membership; drops malformed groups, unknown or ineligible IDs,
 * singletons, and repeat claims.
 */
export function parseConsolidateResult(parsed, ledger) {
  const known = new Set(
    (ledger?.clusters || []).filter((c) => c?.eligible).map((c) => String(c.id)),
  );
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
 * analyze acpx (analyze.js): the `acpx` binary, optional agent
 * positional, ACPX text-output (`--format quiet`, never JSON-RPC),
 * extra args from CA_IMPROVE_ACPX_ARGS, prompt on stdin, model-final
 * JSON extracted strictly from text stdout. */
export function acpxConsolidateInvoke({ prompt, agent = null, model = null, timeoutMs = 120_000 } = {}) {
  const args = buildAcpxArgs({ agent, model: model || modelForRole("consolidate") });
  const result = spawnSync(resolveAcpxBin(), args, { input: prompt, encoding: "utf8", timeout: timeoutMs });
  if (result.error || result.status !== 0) {
    return { status: "failed", error: result.error?.message || `acpx exit ${result.status}` };
  }
  const parsed = extractAcpxFinalJson(result.stdout);
  if (!parsed) {
    return { status: "failed", error: "acpx returned unparseable output" };
  }
  return { status: "ok", result: parsed };
}

/**
 * Run consolidation: acpx-only when >=2 eligible clusters exist.
 * Persists the rendered prompt privately with run/stage metadata.
 * acpx failure/invalid degrades to the deterministic lexical current
 * result with a visible note; it never aborts the run.
 */
export function consolidateLedger(
  ledger,
  { invoke = acpxConsolidateInvoke, promptsDir, stateDir = null, runId = null, minGapEvidence = 2, analyzer = "acpx" } = {},
) {
  const clusters = ledger?.clusters || [];
  const eligible = clusters.filter((c) => c.eligible);
  const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
  if (eligible.length < MIN_CONSOLIDATE_ENTRIES) {
    return { ledger, skipped: "fewer than two eligible gaps", merged: 0, note: "consolidation skipped: fewer than two eligible gaps" };
  }
  if (analyzer === "mock") {
    return { ledger, skipped: "mock analyzer: deterministic lexical identity", merged: 0, note: "consolidation skipped (mock analyzer): deterministic lexical identity" };
  }
  const prompt = buildConsolidatePrompt({ ...ledger, clusters: eligible }, { promptsDir });
  let promptFile = null;
  let persistNote = "";
  if (stateDir) {
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
  let outcome;
  try {
    outcome = invoke({ prompt, clusters: eligible, promptsDir });
  } catch (err) {
    outcome = { status: "failed", error: err?.message || String(err) };
  }
  if (!outcome || outcome.status !== "ok" || !outcome.result) {
    // Support test doubles returning {status:"ok", merges} directly.
    if (outcome && outcome.status === "ok" && Array.isArray(outcome.merges)) {
      const groups = parseConsolidateResult({ merges: outcome.merges }, ledger);
      if (!groups.length) {
        return withPersist({ ledger, failed: "no valid merges", merged: 0, note: "consolidation returned no valid merges; continuing with lexical gap identity for this run", promptFile });
      }
      const merged = mergeClusters(ledger, groups, { minGapEvidence });
      return withPersist({ ledger: merged, merged: groups.reduce((n, g) => n + g.length - 1, 0), note: `consolidation merged ${groups.length} group(s)`, promptFile });
    }
    return withPersist({
      ledger,
      failed: outcome?.error || "consolidation failed",
      merged: 0,
      note: `consolidation failed (${outcome?.error || "unparseable output"}); continuing with lexical gap identity for this run`,
      promptFile,
    });
  }
  const groups = parseConsolidateResult(outcome.result, { ...ledger, clusters: eligible });
  if (!groups.length) {
    const failed = outcome.result && typeof outcome.result === "object" && Array.isArray(outcome.result.merges) ? false : true;
    return withPersist({
      ledger,
      ...(failed ? { failed: "no parseable merge list" } : {}),
      merged: 0,
      note: "consolidation returned no valid merges; continuing with lexical gap identity for this run",
      promptFile,
    });
  }
  const merged = mergeClusters(ledger, groups, { minGapEvidence });
  return withPersist({ ledger: merged, merged: groups.reduce((n, g) => n + g.length - 1, 0), note: `consolidation merged ${groups.length} group(s)`, promptFile });
}
