// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Synthesis adapted from Backpass src/synthesize.js + src/proposal.js
// (commit 0268201), narrowed: the model proposes plans (an eligible cluster,
// an intent, and the sessions behind it) and nothing else. Records, quotes
// and every other durable field come later from annotation. The SOUL is
// read-only context; nothing here writes SOUL, memory files, or skills.

import { renderPrompt } from "./prompts.js";
import { persistPrompt } from "./state.js";

export const MAX_PLANS = 16;
const MAX_INTENT_CHARS = 500;
const PLAN_KEYS = new Set(["id", "kind", "clusterId", "provisionalIntent", "provisionalSources", "provisionalCount"]);
const SAFE_PLAN_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;

function oneLine(text, max = 240) {
  const flat = String(text || "").replace(/\s+/g, " ").trim();
  return flat.length > max ? `${flat.slice(0, max)}...` : flat;
}

function renderEvidence(ledger, evidenceIndex) {
  const lines = [];
  for (const c of ledger.clusters) {
    if (!c.eligible) continue;
    lines.push(`- [${c.id}] sessions=${c.sources.length} :: ${c.proposedInstruction}`);
    for (const source of c.sources.slice(0, 4)) {
      const quote = c.perSource?.[source]?.quote || evidenceIndex.get(source)?.[0]?.quote || c.representativeQuote;
      lines.push(`    "${oneLine(quote)}" (${source})`);
    }
  }
  return lines.length ? lines.join("\n") : "(no eligible gap clusters)";
}

export function renderRejections(rejections) {
  if (!rejections.length) return "(none)";
  return rejections
    .map((r) => {
      const bits = [];
      if (r.clusterId) bits.push(`cluster ${r.clusterId}`);
      if (r.title) bits.push(`title "${r.title}"`);
      if (r.sources) bits.push(`sessions=${Array.isArray(r.sources) ? r.sources.length : r.sources}`);
      if (r.reason) bits.push(`reason ${r.reason}`);
      return `${r.edit ? `[${r.edit}]` : "-"} ${r.title || r.clusterId || "rejected candidate"} (${bits.join("; ") || "no detail"})`;
    })
    .join("\n");
}

function buildSynthesisPrompt(ledger, { evidenceIndex, rejections, transcriptCount, harnessSummary, runNote, soul }) {
  return renderPrompt(
    "synthesis",
    {
      EVIDENCE: renderEvidence(ledger, evidenceIndex),
      REJECTIONS: renderRejections(rejections),
      TRANSCRIPT_COUNT: String(transcriptCount),
      HARNESS_SUMMARY: String(harnessSummary),
      RUN_NOTE: String(runNote || ""),
      SOUL_SNAPSHOT: soul.text,
      SOUL_SHA256: soul.sha256,
    },
  );
}

const isPathLike = (value) => {
  const s = String(value);
  return !s.trim() || s.includes("/") || s.includes("\\") || s.includes("..") || s.startsWith("~") || /^[A-Za-z]:/.test(s);
};

function planErrors(plan, eligibleById, floor) {
  if (!plan || typeof plan !== "object" || Array.isArray(plan)) return ["is malformed (object required)"];
  const extra = Object.keys(plan).filter((key) => !PLAN_KEYS.has(key));
  if (extra.length) return [`carries unexpected field(s) ${extra.join(", ")} (annotation authors records; code assigns storage)`];
  if (plan.kind !== undefined && plan.kind !== "add") return ['kind must be "add"'];
  const clusterId = String(plan.clusterId ?? "").trim();
  if (!clusterId || isPathLike(clusterId)) return ["clusterId is missing or path-like"];
  const cluster = eligibleById.get(clusterId);
  if (!cluster) return [`cluster ${JSON.stringify(clusterId)} is unknown or not eligible`];
  const intent = String(plan.provisionalIntent ?? "").trim();
  if (!intent) return ["provisionalIntent is required"];
  if (intent.length > MAX_INTENT_CHARS) return [`provisionalIntent exceeds ${MAX_INTENT_CHARS} chars`];
  if (!Array.isArray(plan.provisionalSources)) return ["provisionalSources array is required"];
  const sources = [...new Set(plan.provisionalSources.map((s) => String(s).trim()).filter(Boolean))];
  if (sources.length < floor) return [`provisionalSources needs >=${floor} distinct sessions`];
  const clusterSources = new Set(cluster.sources.map(String));
  const foreign = sources.find((s) => isPathLike(s) || !clusterSources.has(s));
  if (foreign !== undefined) return [`provisional source ${JSON.stringify(foreign)} is path-like or not evidence from cluster ${clusterId}`];
  if (plan.provisionalCount !== undefined && Number(plan.provisionalCount) !== sources.length) return ["provisionalCount must equal distinct source count"];
  return [];
}

/**
 * The one schema for a synthesis reply: exactly `{plans: [...]}`, at most
 * MAX_PLANS, each an allowed-key plan on an eligible known cluster with
 * >= floor distinct sources all from that cluster, no path-like ids or
 * sources, a bounded intent, and a unique safe id. Any error rejects the
 * whole reply.
 *
 * @returns {{ok, plans, errors}} plans normalized to {id, kind, clusterId, provisionalIntent, provisionalSources, provisionalCount}
 */
export function validatePlans(reply, { ledger, floor }) {
  if (!reply || typeof reply !== "object" || Array.isArray(reply) || Object.keys(reply).join() !== "plans" || !Array.isArray(reply.plans)) {
    return { ok: false, plans: [], errors: ["synthesis reply must be exactly {plans:[...]}"] };
  }
  if (reply.plans.length > MAX_PLANS) {
    return { ok: false, plans: [], errors: [`synthesis reply exceeds ${MAX_PLANS} plans (got ${reply.plans.length})`] };
  }
  const eligibleById = new Map(ledger.clusters.filter((c) => c.eligible).map((c) => [String(c.id), c]));
  const errors = [];
  const plans = [];
  const seen = new Set();
  reply.plans.forEach((plan, i) => {
    const problems = planErrors(plan, eligibleById, floor);
    const id = plan?.id !== undefined ? String(plan.id).trim() : `e${i + 1}`;
    if (!problems.length && (!SAFE_PLAN_ID.test(id) || id.includes(".."))) problems.push(`id ${JSON.stringify(plan.id)} is not a safe label`);
    if (!problems.length && seen.has(id)) problems.push(`duplicate plan id ${JSON.stringify(id)}`);
    if (problems.length) {
      errors.push(...problems.map((p) => `plans[${i}] ${p}`));
      return;
    }
    seen.add(id);
    const sources = [...new Set(plan.provisionalSources.map((s) => String(s).trim()).filter(Boolean))];
    plans.push({
      id,
      kind: "add",
      clusterId: String(plan.clusterId).trim(),
      provisionalIntent: String(plan.provisionalIntent).trim(),
      provisionalSources: sources,
      provisionalCount: sources.length,
    });
  });
  return errors.length ? { ok: false, plans: [], errors } : { ok: true, plans, errors: [] };
}

/**
 * One synthesis call over the eligible ledger.
 * @returns {{plans, note, failed}} no plans plus a visible note on any failure
 */
export async function synthesize(ledger, { invoke, stateDir, runId, floor, soul, evidenceIndex, rejections, transcriptCount, harnessSummary, runNote }) {
  let reply;
  try {
    const prompt = buildSynthesisPrompt(ledger, { evidenceIndex, rejections, transcriptCount, harnessSummary, runNote, soul });
    persistPrompt(stateDir, { runId, name: "synthesis", prompt, meta: { stage: "synthesis" } });
    reply = await invoke("synthesis", prompt, { ledger, floor });
  } catch (err) {
    return { plans: [], failed: true, note: `synthesis failed (${err.message}); no candidate edits for this run` };
  }
  const check = validatePlans(reply, { ledger, floor });
  if (!check.ok) {
    return { plans: [], failed: true, note: `synthesis plans invalid (${check.errors.join("; ")}); no candidate edits for this run` };
  }
  if (!check.plans.length) {
    return { plans: [], failed: false, note: "synthesis returned zero plans; no provisional record warranted for this run" };
  }
  return { plans: check.plans, failed: false, note: `synthesis validated ${check.plans.length} plan(s)` };
}
