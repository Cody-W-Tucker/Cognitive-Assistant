// Annotation: one model call turns validated plans into verdicts, and a
// `keep` verdict into the complete experience record. Each record is checked
// here against the ledger once; the proposal trusts what passes.

import { renderPrompt } from "./prompts.js";
import { persistPrompt } from "./state.js";

const BODY_MAX_CHARS = 2000;
const RECORD_ID = /^exp-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*-[A-Za-z0-9]{12}$/;
const VERDICTS = new Set(["keep", "drop", "revert"]);
const MAX_SOURCES_PER_PLAN = 8;
const MAX_QUOTES_PER_SOURCE = 2;
const MAX_TOTAL_QUOTE_CHARS = 8000;

/** A stable experience-record id: exp-<slug>-<12-char hash>. */
export function isValidRecordId(id) {
  return typeof id === "string" && RECORD_ID.test(id);
}

/** Exact quotes a record may cite for `source` within `cluster`. */
function allowedQuotes(cluster, source, evidenceIndex) {
  const out = new Set();
  const own = cluster?.perSource?.[source]?.quote;
  if (own) out.add(String(own));
  for (const entry of cluster?.quoteProvenance || []) {
    if (String(entry?.source) === source && entry?.quote) out.add(String(entry.quote));
  }
  for (const p of evidenceIndex.get(source) || []) if (p?.quote) out.add(String(p.quote));
  return out;
}

/**
 * Plans with the exact quotes each may cite, copied whole: the quote budget
 * skips whole quotes and never slices one, since evidence must match byte for byte.
 */
function renderPlans(plans, ledger, evidenceIndex) {
  const clusters = new Map(ledger.clusters.map((c) => [String(c.id), c]));
  let budget = MAX_TOTAL_QUOTE_CHARS;
  return plans
    .map((plan) => {
      const cluster = clusters.get(plan.clusterId);
      const lines = plan.provisionalSources.slice(0, MAX_SOURCES_PER_PLAN).map((source) => {
        const candidates = [...(evidenceIndex.get(source) || []).map((p) => p?.quote), cluster?.perSource?.[source]?.quote];
        const quotes = [];
        for (const quote of candidates) {
          if (typeof quote !== "string" || !quote || quotes.includes(quote) || quotes.length >= MAX_QUOTES_PER_SOURCE) continue;
          if (quote.length > budget) continue;
          budget -= quote.length;
          quotes.push(quote);
        }
        return quotes.length ? quotes.map((q) => `    - [${source}] ${JSON.stringify(q)}`).join("\n") : `    - [${source}] (no staged quote)`;
      });
      return (
        `- [${plan.id}] ${plan.provisionalIntent}\n` +
        `    cluster=${plan.clusterId} eligibleSources=${plan.provisionalSources.join(", ")}\n` +
        `    provisional intent (untrusted): ${plan.provisionalIntent}\n` +
        `    allowed evidence (copy byte-for-byte; same-source only):\n${lines.join("\n")}`
      );
    })
    .join("\n");
}

export function renderAnnotatePrompt(plans, { runId, ledger, evidenceIndex, soul }) {
  return renderPrompt(
    "annotate",
    {
      COUNT: String(plans.length),
      STAGED_CANDIDATES: renderPlans(plans, ledger, evidenceIndex),
      RUN_ID: String(runId),
      SOUL_SNAPSHOT: soul.text,
      SOUL_SHA256: soul.sha256,
    },
  );
}

const blank = (value) => !value || !String(value).trim();

/**
 * Every rule a kept record must meet: a valid id, title, bounded body,
 * counterevidence and compiler implication; an eligible cluster; >=2 distinct
 * sources all from that cluster; every evidence text an exact quote
 * attributable to its own source; and record.sources equal to the set of
 * evidence sources.
 */
export function validateRecord(record, { ledger, evidenceIndex }) {
  const errors = [];
  if (!record || typeof record !== "object") return ["record is required"];
  if (!isValidRecordId(record.id)) errors.push(`record.id must be exp-<slug>-<12-char hash> (got ${JSON.stringify(record.id)})`);
  if (blank(record.title)) errors.push("record.title is required");
  if (blank(record.body)) errors.push("record.body is required");
  else if (String(record.body).length > BODY_MAX_CHARS) errors.push(`record.body exceeds ${BODY_MAX_CHARS} chars`);
  if (blank(record.counterevidence)) errors.push("record.counterevidence is required (or 'none observed')");
  if (blank(record.compilerImplication)) errors.push("record.compilerImplication is required");
  const cluster = ledger.clusters.find((c) => String(c.id) === String(record.clusterId ?? ""));
  if (!cluster) errors.push(`unknown cluster ${JSON.stringify(record.clusterId)}`);
  else if (!cluster.eligible) errors.push(`cluster ${JSON.stringify(record.clusterId)} is not eligible`);
  const clusterSources = new Set((cluster?.sources || []).map(String));
  const sources = new Set(Array.isArray(record.sources) ? record.sources.map(String) : []);
  if (sources.size < 2) errors.push("record.sources needs >=2 distinct sessions");
  for (const s of sources) if (cluster && !clusterSources.has(s)) errors.push(`source ${JSON.stringify(s)} is not evidence from cluster ${cluster.id}`);
  if (!Array.isArray(record.evidence) || !record.evidence.length) {
    errors.push("record.evidence is required");
    return errors;
  }
  const evidenceSources = new Set();
  for (const item of record.evidence) {
    if (!item || typeof item !== "object") {
      errors.push("malformed evidence item");
      continue;
    }
    const source = String(item.source);
    evidenceSources.add(source);
    if (!clusterSources.has(source)) errors.push(`unknown evidence source ${JSON.stringify(item.source)}`);
    else if (!allowedQuotes(cluster, source, evidenceIndex).has(String(item.text))) errors.push(`evidence quote is not an exact quote from source ${source}`);
  }
  if (evidenceSources.size < 2) errors.push("record.evidence needs >=2 distinct sessions");
  if (sources.size !== evidenceSources.size || [...sources].some((s) => !evidenceSources.has(s))) {
    errors.push("record.sources must exactly match the evidence source set");
  }
  return errors;
}

/**
 * One annotate call over the plans. Every plan needs a verdict; any missing
 * verdict or invalid kept record fails the whole annotation, so a partially
 * trusted reply never reaches the proposal.
 *
 * @returns {{kept: [{plan, annotation, record}], annotated, failed, note}}
 */
export async function annotate(plans, { invoke, stateDir, runId, ledger, evidenceIndex, soul }) {
  const fail = (reason) => ({ kept: [], annotated: 0, failed: true, note: `annotate failed (${reason}); no candidate edits for this run` });
  let reply;
  try {
    const prompt = renderAnnotatePrompt(plans, { runId, ledger, evidenceIndex, soul });
    persistPrompt(stateDir, { runId, name: "annotate", prompt, meta: { stage: "annotate" } });
    reply = await invoke("annotate", prompt, { plans, ledger, evidenceIndex });
  } catch (err) {
    return fail(err.message);
  }
  if (!Array.isArray(reply?.annotations)) return fail("annotate returned no annotations");
  const byId = new Map(reply.annotations.filter((a) => a && typeof a === "object").map((a) => [String(a.id), a]));
  const kept = [];
  for (const plan of plans) {
    const annotation = byId.get(plan.id);
    const verdict = String(annotation?.verdict ?? "").trim();
    if (!annotation) return fail(`missing annotation for ${plan.id}`);
    if (!VERDICTS.has(verdict)) return fail(`annotation for ${plan.id} has verdict ${JSON.stringify(annotation.verdict)} (want keep|drop|revert)`);
    if (verdict !== "keep") continue;
    const errors = validateRecord(annotation.record, { ledger, evidenceIndex });
    if (!errors.length) {
      const record = annotation.record;
      const sources = new Set(plan.provisionalSources);
      if (String(record.clusterId) !== plan.clusterId) errors.push("record.clusterId must match the plan cluster");
      for (const source of [...record.sources, ...record.evidence.map((item) => item.source)]) {
        if (!sources.has(String(source))) errors.push(`source ${JSON.stringify(source)} is not in plan.provisionalSources`);
      }
    }
    if (errors.length) return fail(`annotation invalid for ${plan.id} (${errors.join("; ")})`);
    kept.push({ plan, annotation: { verdict, reason: String(annotation.reason || annotation.rationale || "") }, record: annotation.record });
  }
  return { kept, annotated: plans.length, failed: false, note: "" };
}
