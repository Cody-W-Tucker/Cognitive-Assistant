# Alignment Profile

The alignment profile is a cross-profile synthesis layer that produces the
orchestrator translation layer (`INTERACTION_POSTURE.md` and `SOUL.md`) and a
personalized artifact verification spec from both the existential and
operational profiles. It is not registered as a `LayerProfile`; it has no
workspace, questions, or CLI `--profile` value.

## Purpose

The alignment profile solves one question: what makes an artifact
production-ready _for this user_? It produces a **personalized artifact
verification checklist** that a downstream verifier (`rlm` via
`verify-alignment`) uses to score AI-generated artifacts.

The checklist has two layers:

1. **Generic artifact-readiness checklist** (universal SOP) - 10 fixed items that apply to any artifact: purpose stated, scope bounded, claims grounded, gaps surfaced, acceptance defined, structure earns its keep, internally consistent, form matches request, language precise, self-contained.
2. **Personalization** - unified skills from `workspaces/skills` overlay onto each checklist item as user-specific cues for what "satisfied" and "failed" look like in practice.

The checklist skeleton lives in `profiles/alignment/prompts/seed.md`. The
verifier role and response format live in `core/alignment_spec.py` (preamble +
postamble). The LLM only generates the personalized middle.

## Pipeline

The pipeline is ordered and deterministic:

1. The translation layer is generated first: the existential and operational
   `human_profile.md` files feed `interaction_posture_seed.md` to produce
   `INTERACTION_POSTURE.md`, then both profile sources plus the posture feed
   `soul_seed.md` to produce `SOUL.md` - the durable orchestrator
   constitution.
2. `build-alignment-spec` then reads unified skills and produces the
   personalized verification spec.

## Files

| Path                                                          | Role                                                                                                                                            |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `profiles/alignment/prompts/seed.md`               | Compiler instructions: fixed checklist taxonomy + per-item output structure.                                                                    |
| `profiles/alignment/prompts/interaction_posture_seed.md` | Compiler instructions for inferring the orchestrator counterpart posture from both profiles.                                                            |
| `profiles/alignment/prompts/soul_seed.md`          | Compiler instructions for generating the orchestrator translation-layer soul from both profiles plus the interaction posture.                             |
| `core/alignment_spec.py`                           | Loads unified skills from `workspaces/skills`, calls the LLM with the seed, prepends/appends static verifier role and response format, writes the final spec. |
| `core/translation_layer_creator.py`                | Loads both profile human profiles, infers the interaction posture, generates the orchestrator soul, writes `INTERACTION_POSTURE.md` and `SOUL.md`.             |
| `scripts/verify_alignment.sh`                      | Runtime tool. Passes the spec + an artifact to `rlm` for evaluation.                                                                            |
| `workspaces/alignment/artifacts/alignment_spec.md` | The generated, committed verification spec.                                                                                                     |
| `workspaces/alignment/artifacts/INTERACTION_POSTURE.md` | The generated orchestrator counterpart posture intermediate artifact.                                                                                     |
| `workspaces/alignment/artifacts/SOUL.md`           | The generated orchestrator translation-layer soul.                                                                                              |

| `workspaces/skills/<profile>/<skill>/SKILL.md`     | One unified skill document per profile/skill pair.                                                                                        |

## Build the translation layer

Requires `build-prompts` to have been run for both profiles so the
`human_profile.md` source files exist.

```bash
python -m core build-translation-layer
```

Output:
- `workspaces/alignment/artifacts/INTERACTION_POSTURE.md` - inferred orchestrator counterpart posture
- `workspaces/alignment/artifacts/SOUL.md` - orchestrator translation-layer soul

## Build the spec

Requires unified skills in `workspaces/skills` from `build-skills`.

```bash
python -m core build-alignment-spec
```

Output:
- `workspaces/alignment/artifacts/alignment_spec.md` - the personalized verification spec

## Full regeneration order

```bash
python -m core --profile existential ingest-substrate --graph /path/to/graph.json
python -m core --profile existential ask-questions
python -m core --profile existential build-prompts
python -m core --profile existential build-skills

python -m core --profile operational ingest-corpus
python -m core --profile operational ask-questions
python -m core --profile operational build-prompts
python -m core --profile operational build-skills
python -m core build-translation-layer
python -m core build-alignment-spec
```

## Verify alignment at runtime

`scripts/verify_alignment.sh` passes the generated spec plus an artifact to
`rlm` for evaluation and returns `VERDICT: SHIP | TIGHTEN | REWORK` with
per-item scores and corrections.
