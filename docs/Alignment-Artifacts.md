# Alignment Artifacts

The cross-profile stages sit above both layer profiles. They read every
profile's output and write to `workspaces/alignment/artifacts/` (paths in
`core/paths.py`). Their prompts are in `profiles/alignment/prompts/`, which is
not a profile: it has no questions, workspace or `--profile` value.

| Artifact | Built by | Role |
| --- | --- | --- |
| `INTERACTION_POSTURE.md` | `build-translation-layer` | Third-person description of the counterpart the agent should be; grounds the SOUL |
| `SOUL.md` | `build-translation-layer` | The bootstrap SOUL: first-person orchestrator constitution (persona, core truths, boundaries, mode detection, voice) |
| `absorbed.json` | `build-translation-layer` | Ids of the lineage records this SOUL already took into account |
| `alignment_spec.md` | `build-alignment-spec` | Personalized artifact verification checklist |

## Translation layer (`build-translation-layer`)

`core/translation_layer_creator.py`, two model calls:

1. **Posture.** Every registered profile's `human_profile.md`, each wrapped in
   `<profile_source layer="...">`, fills `interaction_posture_seed.md`
   (`{profile_sources}`) and produces `INTERACTION_POSTURE.md`.
2. **SOUL.** The same sources, the new posture and the full runtime lineage
   fill `soul_seed.md` (`{profile_sources}`, `{interaction_posture}`,
   `{lineage}`) and produce `SOUL.md`.

The lineage is every experience record under `<CA home>/experience/authored/`,
marked `adopted` or `withdrawn` (see [Living SOUL](Living-SOUL.md)). A
rebootstrap therefore sees what was learned in use, including changes that
were tried and reverted. The ids of the adopted records go to `absorbed.json`
beside `SOUL.md`; the living SOUL leaves those records out of its learned
section so they are not counted twice. This is the only way lineage enters the
bootstrap: `build-prompts` and the profile stages do not read it.

Requires `build-prompts` to have run for every profile. The generated files
are committed; the bootstrap SOUL is never edited by the runtime.

## Alignment spec (`build-alignment-spec`)

`core/alignment_spec.py` answers: what makes an artifact production-ready for
this person?

1. Every `SKILL.md` in `workspaces/skills/` is wrapped as
   `<skill group="..." source_profile="..." name="...">` and substituted into
   `seed.md` (`{skills_content}`).
2. One model call returns the personalized middle: a fixed 10-item checklist
   (clear purpose, defined scope, grounded claims, gaps acknowledged, success
   criteria, efficient structure, internal consistency, matches the request,
   precise language, self-contained), each item with "Satisfied when",
   "Failed when" and "Fix" cues drawn from the skills.
3. A static preamble (the verifier role) and postamble (scoring and output
   format) from `core/alignment_spec.py` are wrapped around it. Replies under
   200 characters are rejected.

The verifier scores each item PASS / WEAK / FAIL and returns SHIP (all pass,
or one minor weak), TIGHTEN (weak items with corrections, no fail) or REWORK
(any fail, or compounding weak items).

The SOUL and posture are not inputs to the spec; skills are the
personalization source. Regenerate the spec whenever the skill store changes.
Downstream consumers get it through the flake as
`lib.artifacts.alignment.spec`.

## Regeneration order

```bash
python -m core --profile existential ask-questions
python -m core --profile existential build-prompts
python -m core --profile operational ask-questions
python -m core --profile operational build-prompts
python -m core update   # skills, tool specs, translation layer, alignment spec
```
