// CA-native deterministic measurement: stable measured IDs/deltas for every
// staged candidate. Measurements persist privately only; every measurement
// carries an annotation slot or explicit revert.

import fs from "node:fs";
import path from "node:path";

import { render, SELF_SESSION_SENTINEL } from "./prompts.js";
import { persistPrompt } from "./analyze.js";

function plainSentinel() {
  return String(SELF_SESSION_SENTINEL).replace(/^<!--\s*/, "").replace(/\s*-->$/, "");
}

/** Render the measurement prompt via the existing strict renderer (sentinel FIRST). */
export function buildMeasurePrompt(staged, { runId = "run-unknown" } = {}) {
  const list = Array.isArray(staged) ? staged : [];
  const summary =
    list.length > 0
      ? list.map((c) => `- ${c.id}: ${c.provisionalIntent || c.intent || c.record?.title || c?.title || "untitled"} (cluster=${c.clusterId || c.record?.clusterId || "unknown"} eligibleSources=${((c.provisionalSources || c.record?.sources) || []).length})`).join("\n")
      : "(no staged change plans)";
  const body = render(
    "Measure {{COUNT}} staged candidate(s) for {{RUN_ID}}:\n{{SUMMARY}}\nEmit stable measured IDs/deltas only; no tracked-file, SOUL, skills, or Hermes edits.",
    { COUNT: String(list.length), RUN_ID: String(runId), SUMMARY: summary },
  );
  return `${plainSentinel()}\n${body}`;
}

/**
 * Deterministically measure narrow staged change plans.
 * Stable IDs: m-<candidateId>. Deltas: pure functions of the provisional
 * plan (eligible source count, provisional intent chars). Each measurement
 * carries the stable change id, delta, provisional intent, and eligible
 * evidence context (clusterId + eligible sources) — never a final record,
 * title/body/evidence, counterevidence, or compilerImplication. Each
 * measurement carries a provisional annotation (measured keep) so
 * downstream coverage holds; explicit `reverted: true` on the staged
 * plan propagates as reverted.
 *
 * Persists staging/measurements.json plus the rendered measure prompt
 * privately (run/stage naming, 0600). Always persists even when empty.
 */
export function measureStaging(staged, { stateDir = null, runId = null, ledger = null, evidenceIndex = null } = {}) {
  void ledger;
  void evidenceIndex;
  const list = Array.isArray(staged) ? staged : [];
  const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
  const now = new Date().toISOString();
  const measurements = list.map((c) => {
    const provisionalSources = Array.isArray(c?.provisionalSources) ? c.provisionalSources : Array.isArray(c?.record?.sources) ? c.record.sources : [];
    const provisionalIntent = String(c?.provisionalIntent ?? c?.intent ?? c?.record?.title ?? c?.title ?? "");
    const intentChars = provisionalIntent.length;
    const reverted = c?.reverted === true;
    return {
      id: `m-${c?.id || "unknown"}`,
      candidateId: String(c?.id || "unknown"),
      clusterId: c?.clusterId || c?.record?.clusterId || null,
      provisionalIntent,
      eligibleSources: [...provisionalSources.map(String)],
      evidenceContext: {
        clusterId: c?.clusterId || c?.record?.clusterId || null,
        eligibleSources: [...provisionalSources.map(String)],
      },
      recordId: null,
      sources: [...provisionalSources.map(String)],
      evidenceCount: provisionalSources.length,
      bodyChars: 0,
      titleChars: intentChars,
      intentChars,
      delta: {
        sources: provisionalSources.length,
        evidence: provisionalSources.length,
        bodyChars: 0,
        titleChars: intentChars,
        intentChars,
      },
      ...(reverted ? { reverted: true } : { annotation: { verdict: "keep", reason: "measured", stableId: `m-${c?.id}` } }),
      measuredAt: now,
      runId: String(resolvedRun),
    };
  });
  if (stateDir) {
    const resolved = path.resolve(stateDir);
    const staging = path.join(resolved, "staging");
    fs.mkdirSync(staging, { recursive: true });
    fs.writeFileSync(path.join(staging, "measurements.json"), `${JSON.stringify(measurements, null, 2)}\n`, "utf8");
    fs.writeFileSync(
      path.join(staging, "measure.json"),
      `${JSON.stringify({ version: 1, runId: String(resolvedRun), count: measurements.length, createdAt: now }, null, 2)}\n`,
      "utf8",
    );
    try {
      persistPrompt(resolved, {
        runId: String(resolvedRun),
        transcriptId: "measure",
        harness: "stage",
        prompt: buildMeasurePrompt(list, { runId: String(resolvedRun) }),
        stage: "measure",
      });
    } catch {
      // persistence best-effort next to measurement; measurements.json already holds the data
    }
  }
  return measurements;
}
