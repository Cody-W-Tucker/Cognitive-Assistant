// SPDX: MIT — CA role models, adapted from Backpass src/config.js DEFAULT_LADDERS
// (commit 0268201). Backpass walks a multi-agent ladder. This runtime stays
// Pi-through-ACPX only, so each role keeps Backpass's preferred model and
// skips the other agents. Distillation itself is local and has no model.

/** Cheap per-trace and clustering role. Backpass analysis rung 1. */
export const ANALYSIS_MODEL = "openai-codex/gpt-5.6-luna";

/**
 * Stronger judgment role. Backpass synthesis rung 1. Consolidation groups
 * evidence; synthesis and annotation decide what becomes a record.
 */
export const SYNTHESIS_MODEL = "openai-codex/gpt-5.6-sol";

export const ROLE_MODELS = {
  analysis: ANALYSIS_MODEL,
  consolidate: ANALYSIS_MODEL,
  synthesis: SYNTHESIS_MODEL,
  annotate: SYNTHESIS_MODEL,
};

/**
 * Model for one pipeline role. An explicit role override wins. Otherwise the
 * Backpass-shaped default applies. Unknown roles fail closed.
 * @param {"analysis"|"consolidate"|"synthesis"|"annotate"} role
 * @param {string | null} [override]
 * @returns {string}
 */
export function modelForRole(role, override = null) {
  if (override) return String(override);
  const model = ROLE_MODELS[role];
  if (!model) throw new Error(`unknown model role: ${role}`);
  return model;
}
