// `--analyzer mock`: a deterministic stand-in for the model behind the same
// invoke interface, so a mock run exercises every stage and validator a real
// run does with zero model traffic. Every trace reports the same gap, which
// makes the evidence floor reachable from small fixtures.

import { shortHash, slugify } from "./state.js";

const GAP = "sessions re-derive project context from scratch";

function analysis({ trace }) {
  const firstLine = String(trace.distilled || "").split("\n").find((line) => line.trim()) || "";
  return {
    status: "ok",
    positive: [{ instruction: "exp-context-bootstrap", quote: firstLine.slice(0, 200), effect: "session made progress from a standing start" }],
    negative: [],
    gaps: [{ proposedInstruction: "exp-context-bootstrap", mistake: GAP, quote: GAP, recurrenceRisk: "every new session pays the same bootstrap cost" }],
  };
}

function synthesis({ ledger }) {
  const eligible = ledger.clusters.filter((c) => c.eligible);
  return {
    plans: eligible.map((c, i) => ({
      id: `e${i + 1}`,
      kind: "add",
      clusterId: c.id,
      provisionalIntent: c.proposedInstruction,
      provisionalSources: [...c.sources],
    })),
  };
}

function annotateReply({ plans, ledger, evidenceIndex }) {
  return {
    annotations: plans.map((plan) => {
      const cluster = ledger.clusters.find((c) => c.id === plan.clusterId);
      const evidence = plan.provisionalSources.map((source) => {
        const first = (evidenceIndex.get(source) || [])[0];
        return {
          polarity: "negative",
          text: cluster.perSource?.[source]?.quote || first?.quote || cluster.representativeQuote,
          effect: cluster.perSource?.[source]?.mistake || cluster.mistake,
          moment: first?.effect || "",
          source,
        };
      });
      return {
        id: plan.id,
        verdict: "keep",
        reason: cluster.mistake || plan.provisionalIntent,
        record: {
          id: `exp-${slugify(plan.provisionalIntent).slice(0, 40).replace(/-+$/, "")}-${shortHash(plan.clusterId)}`,
          title: plan.provisionalIntent,
          body: `Recurring gap seen in ${plan.provisionalSources.length} session(s): ${cluster.mistake}`,
          sources: plan.provisionalSources,
          clusterId: plan.clusterId,
          evidence,
          counterevidence: "none observed",
          compilerImplication: "compiler appends this record to the experience block; no SOUL, skill, or Hermes changes.",
        },
      };
    }),
  };
}

const REPLIES = { analysis, consolidate: () => ({ merges: [] }), synthesis, annotate: annotateReply };

export async function mockInvoke(role, _prompt, context) {
  return REPLIES[role](context);
}
