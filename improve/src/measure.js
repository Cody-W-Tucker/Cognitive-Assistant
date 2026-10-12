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
      ? list.map((c) => `- ${c.id}: ${c.title || c.record?.title || "untitled"} (sources=${(c.record?.sources || []).length})`).join("\n")
      : "(no staged candidates)";
  const body = render(
    "Measure {{COUNT}} staged candidate(s) for {{RUN_ID}}:\n{{SUMMARY}}\nEmit stable measured IDs/deltas only; no tracked-file, SOUL, skills, or Hermes edits.",
    { COUNT: String(list.length), RUN_ID: String(runId), SUMMARY: summary },
  );
  return `${plainSentinel()}\n${body}`;
}

/**
 * Deterministically measure staged candidates.
 * Stable IDs: m-<candidateId>. Deltas: pure functions of the staged record
 * (source/evidence counts, body/title chars). Each measurement carries an
 * annotation (measured keep) so downstream coverage holds; explicit
 * `reverted: true` on the staged candidate propagates as reverted.
 *
 * Persists staging/measurements.json plus the rendered measure prompt
 * privately (run/stage naming, 0600). Always persists even when empty.
 */
export function measureStaging(staged, { stateDir = null, runId = null } = {}) {
  const list = Array.isArray(staged) ? staged : [];
  const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
  const now = new Date().toISOString();
  const measurements = list.map((c) => {
    const record = c?.record || {};
    const evidence = Array.isArray(c?.evidence) ? c.evidence : Array.isArray(record.evidence) ? record.evidence : [];
    const sources = Array.isArray(record.sources) ? record.sources : [];
    const bodyChars = String(record.body || "").length;
    const titleChars = String(record.title || c?.title || "").length;
    const reverted = c?.reverted === true;
    return {
      id: `m-${c?.id || "unknown"}`,
      candidateId: String(c?.id || "unknown"),
      recordId: record.id || null,
      clusterId: record.clusterId || null,
      sources: [...sources.map(String)],
      evidenceCount: evidence.length,
      bodyChars,
      titleChars,
      delta: {
        sources: sources.length,
        evidence: evidence.length,
        bodyChars,
        titleChars,
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
