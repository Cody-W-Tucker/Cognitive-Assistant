# Alignment

Artifact verification — checks whether an AI-generated artifact (spec, plan, document, code change, copy, summary) is production-ready against this user's personalized standards.

Alignment sits **above** the layer profile system. The builders live in `core`, read artifacts from both the existential and operational profiles, and produce cross-profile outputs. They are invoked without `--profile`.

## Architecture

The verification spec has two layers:

1. **Generic artifact-readiness checklist** (universal SOP) — 10 fixed items that apply to any artifact: purpose stated, scope bounded, claims grounded, gaps surfaced, acceptance defined, structure earns its keep, internally consistent, form matches request, language precise, self-contained.
2. **Personalization** — unified skills from `workspaces/skills` overlay onto each checklist item as user-specific cues for what "satisfied" and "failed" look like in practice.

The checklist skeleton lives in `profiles/alignment/prompts/seed.md`. The verifier role and response format live in `core/alignment_spec.py` (preamble + postamble). The LLM only generates the personalized middle.

The SOUL artifact works differently:

1. The existential and operational `human_profile.md` files act as source material.
2. `profiles/alignment/prompts/soul_seed.md` defines the SOUL.md target shape and compression rules.
3. `core/soul_creator.py` asks the LLM to merge both source artifacts into one durable identity document for Hermes/OpenClaw-style agents.

## Files

| File                                               | Purpose                                                                                                                                         |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `profiles/alignment/prompts/seed.md`               | Compiler instructions: fixed checklist taxonomy + per-item output structure.                                                                    |
| `profiles/alignment/prompts/soul_seed.md`          | Compiler instructions for generating a durable SOUL.md from the existential and operational human profiles.                                      |
| `core/alignment_spec.py`                           | Loads unified skills from `workspaces/skills`, calls the LLM with the seed, prepends/appends static verifier role and response format, writes the final spec. |
| `core/soul_creator.py`                             | Loads the existential and operational human profiles, calls the LLM with the soul seed, writes the final SOUL.md artifact.                     |
| `scripts/verify_alignment.sh`                      | Runtime tool. Passes the spec + an artifact to `rlm` for evaluation.                                                                            |
| `workspaces/alignment/artifacts/alignment_spec.md` | The generated, committed verification spec.                                                                                                     |
| `workspaces/alignment/artifacts/SOUL.md`           | The generated, committed durable identity document for Hermes/OpenClaw-style agents.                                                            |

## Build the spec

Requires unified skills to exist in `workspaces/skills` from `build-skills` or a third-party import.

```bash
python -m core build-alignment-spec
python -m core build-alignment-spec --output /path/to/alt-spec.md
```

The default output path is `workspaces/alignment/artifacts/alignment_spec.md`.

## Build the soul

Requires `build-prompts` to have been run for both profiles so the
`human_profile.md` source files exist.

```bash
python -m core build-soul
python -m core build-soul --output /path/to/SOUL.md
```

The default output path is `workspaces/alignment/artifacts/SOUL.md`.

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

## Regenerating after skill changes

The spec is a downstream artifact of the unified skills. Whenever you change `workspaces/skills`, regenerate the alignment spec:

```bash
python -m core --profile existential build-skills
python -m core --profile operational build-skills
python -m core build-alignment-spec
```
