# Overview

The Cognitive Assistant (CA) turns a person's own notes and work history into
the guidance an AI agent (Hermes) runs with: a SOUL, an interaction posture,
skills, tool specs and an alignment spec. It then keeps improving that SOUL
from the agent's real sessions.

The project has two halves.

1. **Bootstrap pipeline (this repo).** Profile stages answer a question set
   from QMD retrieval, synthesize a human profile per layer, derive skills and
   tool specs, and finally build the bootstrap SOUL, interaction posture and
   alignment spec. Outputs are committed under `workspaces/`.
2. **Runtime (CA home).** After bootstrap, everything that changes lives
   outside the repo under CA home (`$CA_HOME`, default
   `$XDG_DATA_HOME/cognitive-assistant`). The improvement loop analyzes
   sessions and proposes experience records; accepted records are compiled
   into the *living SOUL* that Hermes actually reads. Nothing flows back into
   the repo except through a deliberate rebootstrap.

## Pipeline

```text
profiles/<name>/questions.csv
        |  ask-questions      (QMD retrieval + one model call per question)
        v
workspaces/<name>/data/questions_with_answers_qmd_<ts>.csv
        |  build-prompts      (3 provider drafts -> 1 synthesis)
        v
workspaces/<name>/artifacts/human_profile.md
        |  build-skills       -> workspaces/skills/<name>/<slug>/SKILL.md
        |  build-tool-specs   -> workspaces/operational/artifacts/tool_specs/*.md
        v
both human profiles + runtime lineage
        |  build-translation-layer
        v
workspaces/alignment/artifacts/{INTERACTION_POSTURE.md, SOUL.md, absorbed.json}
all skills
        |  build-alignment-spec
        v
workspaces/alignment/artifacts/alignment_spec.md

runtime:  sessions -> improve-run -> proposal -> improve-apply -> experience records
          bootstrap SOUL + active records -> soul compile -> <CA home>/soul/current.md
```

The operational profile can also normalize raw exports first with
`ingest-corpus` (see [Layer Profiles](Layer-Profiles.md)). `update` runs
`build-prompts`, `build-skills`, `build-tool-specs`, then the two cross-profile
stages; it does not re-run `ask-questions` or `ingest-corpus`.

## Repository layout

```text
core/                 the Python pipeline and CLI (python -m core)
  config.py           LayerProfile declarations (one per profile)
  paths.py            repo paths for skills/alignment and CA home locations
  llm.py              model calls for the bootstrap stages
  improve.py          launches the Node runtime, applies decisions, auto cycle
  experience.py       accepted change records (the lineage)
  living_soul.py      living SOUL generations
  outcome.py          per-generation session outcome check
  journal.py          private lineage journal
improve/              Node improvement runtime (zero dependencies)
  bin/ca-improve.js   runtime CLI called by core/improve.py
  src/                harnesses, distill, analyze, fold, consolidate, synthesize, annotate
  prompts/            analysis, consolidate, synthesis, annotate prompts
profiles/<name>/      profile inputs: questions.csv, prompts/
profiles/alignment/   prompts for the translation layer and alignment spec
workspaces/<name>/    profile data/ (gitignored) and artifacts/
workspaces/skills/    the skill store
workspaces/alignment/ bootstrap SOUL, posture, alignment spec
tests/                Python unit tests
improve/tests/        Node tests
flake.nix             packages, NixOS/Home Manager modules, dev shell
```

## Glossary

- **Layer profile**: a `LayerProfile` in `core/config.py` (`existential` or
  `operational`) that declares a layer's prompts, QMD collections, skills and
  tool specs.
- **QMD**: local markdown search CLI; `ask-questions` retrieves evidence from
  it and refuses to answer when retrieval is missing, empty or stale.
- **Human profile**: `workspaces/<name>/artifacts/human_profile.md`, the
  synthesized description of the person for one layer.
- **Bootstrap SOUL**: `workspaces/alignment/artifacts/SOUL.md`, built by
  `build-translation-layer`.
- **Living SOUL**: the bootstrap SOUL plus active learned records, compiled
  into numbered generations under `<CA home>/soul/`.
- **Experience record**: one accepted, evidence-backed instruction under
  `<CA home>/experience/authored/<id>.md`. The set of records is the lineage.
- **Proposal**: the improvement runtime's output (`<CA home>/improve/proposal.json`),
  a list of candidate edits each carrying a complete record.
- **Alignment spec**: a personalized artifact verification checklist at
  `workspaces/alignment/artifacts/alignment_spec.md`.
