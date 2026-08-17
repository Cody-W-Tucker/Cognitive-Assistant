# Alignment

Artifact verification — checks whether an AI-generated artifact (spec, plan, document, code change, copy, summary) is production-ready against this user's personalized standards.

Alignment sits **above** the layer profile system. The builders live in `core`, read artifacts from both the existential and operational profiles, and produce cross-profile outputs. They are invoked without `--profile`.

## Architecture

The verification spec has two layers:

1. **Generic artifact-readiness checklist** (universal SOP) — 10 fixed items that apply to any artifact: purpose stated, scope bounded, claims grounded, gaps surfaced, acceptance defined, structure earns its keep, internally consistent, form matches request, language precise, self-contained.
2. **Personalization** — unified skills from `workspaces/skills` and agent souls from `workspaces/alignment/artifacts/agents/` overlay onto each checklist item as user-specific cues for what "satisfied" and "failed" look like in practice.

The checklist skeleton lives in `profiles/alignment/prompts/seed.md`. The verifier role and response format live in `core/alignment_spec.py` (preamble + postamble). The LLM only generates the personalized middle.

The skill pipeline (per-profile) works differently:

1. Each profile's `human_profile.md` acts as source material.
2. `build-skills` generates canonical skill documents from the profile's declared skill specs.
3. Generated skills land in `workspaces/skills/<profile>/<skill>/SKILL.md`.

The agent soul pipeline (cross-profile) works differently still:

1. The translation layer is generated first: the existential and operational
   `human_profile.md` files feed `soul_archetype_seed.md` to produce
   `SOUL_ARCHETYPE.md`, then both profile sources plus the archetype feed
   `soul_seed.md` to produce `SOUL.md` — the orchestrator constitution that
   specialist agents inherit.
2. `profiles/alignment/archetypes/` contains the predefined archetype catalog.
   Each archetype declares a stable slug, a real operating contract (purpose,
   job-to-be-done, outcome, scope, authority, quality/evidence expectations),
   and canonical skill assignments.
3. `profiles/alignment/prompts/archetype_selection_seed.md` instructs the LLM
   to select applicable archetypes from the catalog, calibrate them to the
   user, and assign skills from each archetype's declared canonical set.
   Unknown archetype slugs and unknown skill slugs fail with clear errors.
4. `profiles/alignment/prompts/agent_soul_seed.md` defines the per-agent soul
   target shape and compression rules. Specialist souls consume the full
   archetype contract, user calibration, the translation layer, and scoped
   skill material — not the full raw profile sources.
5. `core/soul_creator.py` runs two stages: archetype selection (producing
   `persona_map.md`), then per-agent soul generation (one file per selected
   archetype under `agents/`).
6. Runtime orchestration, tool access enforcement, agent-to-agent routing,
   and trace logging are explicitly deferred and not implemented in this stage.

## Files

| File                                               | Purpose                                                                                                                                         |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `profiles/alignment/prompts/seed.md`               | Compiler instructions: fixed checklist taxonomy + per-item output structure.                                                                    |
| `profiles/alignment/prompts/soul_archetype_seed.md` | Compiler instructions for inferring the orchestrator archetype from both profiles.                                                            |
| `profiles/alignment/prompts/soul_seed.md`          | Compiler instructions for generating the orchestrator translation-layer soul from both profiles plus the archetype.                             |
| `profiles/alignment/prompts/archetype_selection_seed.md` | Compiler instructions for selecting archetypes from the catalog, calibrating them to the user, and assigning skills. |
| `profiles/alignment/prompts/agent_soul_seed.md`    | Compiler instructions for generating a per-agent soul document from the archetype contract, calibration, translation layer, and skill material. |
| `profiles/alignment/archetypes/*.json`             | Predefined archetype catalog. Each file declares one archetype's operating contract and canonical skill assignments. |
| `core/alignment_spec.py`                           | Loads unified skills from `workspaces/skills` and agent souls from `workspaces/alignment/artifacts/agents/`, calls the LLM with the seed, prepends/appends static verifier role and response format, writes the final spec. |
| `core/translation_layer_creator.py`                | Loads both profile human profiles, infers the archetype, generates the orchestrator soul, writes `SOUL_ARCHETYPE.md` and `SOUL.md`.             |
| `core/soul_creator.py`                             | Loads the translation layer and archetype catalog, selects applicable archetypes, generates per-agent souls, writes persona_map.md and agents/<slug>.md. |
| `core/archetype_catalog.py`                        | Loads and validates the predefined archetype catalog from `profiles/alignment/archetypes/`. |
| `scripts/verify_alignment.sh`                      | Runtime tool. Passes the spec + an artifact to `rlm` for evaluation.                                                                            |
| `workspaces/alignment/artifacts/alignment_spec.md` | The generated, committed verification spec.                                                                                                     |
| `workspaces/alignment/artifacts/SOUL_ARCHETYPE.md` | The generated orchestrator archetype intermediate artifact.                                                                                     |
| `workspaces/alignment/artifacts/SOUL.md`           | The generated orchestrator translation-layer soul.                                                                                              |
| `workspaces/alignment/artifacts/persona_map.md`    | The generated persona map intermediate artifact.                                                                                                |
| `workspaces/alignment/artifacts/agents/<slug>.md`  | One per-agent soul document.                                                                                                                    |

| `workspaces/skills/<profile>/<skill>/SKILL.md`     | One unified skill document per profile/skill pair.                                                                                        |

## Build skills

Requires `build-prompts` to have been run for a profile so the `human_profile.md` source file exists.

```bash
python -m core --profile existential build-skills
python -m core --profile operational build-skills
```

Output:
- `workspaces/skills/<profile>/<skill>/SKILL.md` — one per declared skill spec

## Build agent souls

Requires the translation layer to have been generated first and
`build-prompts` to have been run for both profiles so the
`human_profile.md` source files exist. Also requires canonical skills
in `workspaces/skills/` (from `build-skills`) since each archetype's
canonical skill assignments must resolve.

```bash
python -m core build-translation-layer
python -m core build-agents
```

Output:
- `workspaces/alignment/artifacts/persona_map.md` — intermediate, human-readable; lists selected archetypes with calibrations and skill assignments
- `workspaces/alignment/artifacts/agents/<slug>.md` — one per selected archetype

## Build the translation layer

Requires `build-prompts` to have been run for both profiles so the
`human_profile.md` source files exist.

```bash
python -m core build-translation-layer
```

Output:
- `workspaces/alignment/artifacts/SOUL_ARCHETYPE.md` — inferred orchestrator archetype
- `workspaces/alignment/artifacts/SOUL.md` — orchestrator translation-layer soul

## Build the spec

Requires unified skills in `workspaces/skills` from `build-skills` and agent souls in `workspaces/alignment/artifacts/agents/` from `build-agents`.

```bash
python -m core build-alignment-spec
python -m core build-alignment-spec --output /path/to/alt-spec.md
```

The default output path is `workspaces/alignment/artifacts/alignment_spec.md`.

## Verify an artifact

```bash
# From a file
scripts/verify_alignment.sh --file path/to/artifact.md

# From stdin
echo "$ARTIFACT" | scripts/verify_alignment.sh --stdin
```

`verify_alignment.sh` requires the `rlm` binary in `PATH`. The spec is resolved from `$ALIGNMENT_SPEC` if set, otherwise from `workspaces/alignment/artifacts/alignment_spec.md`.

## Output format

The verifier returns:

```
VERDICT: SHIP | TIGHTEN | REWORK

| # | Checklist Item | Score | Evidence | Fix |
|---|----------------|-------|----------|-----|

CORRECTIONS (if TIGHTEN):
- [imperative instructions]

REWORK (if REWORK):
- [structural problem]
- [what the artifact should do instead]
```

- **SHIP** — all PASS, or one minor WEAK with no correction needed.
- **TIGHTEN** — one or more WEAK with actionable corrections; no FAIL.
- **REWORK** — any FAIL, or compounding WEAK indicating the artifact does not
  hold together.

## Regenerating after skill or agent changes

The spec is a downstream artifact of both unified skills and agent souls. Whenever you change `workspaces/skills` or regenerate agent souls, regenerate the alignment spec:

```bash
python -m core --profile existential build-skills
python -m core --profile operational build-skills
python -m core build-translation-layer
python -m core build-agents
python -m core build-alignment-spec
```
