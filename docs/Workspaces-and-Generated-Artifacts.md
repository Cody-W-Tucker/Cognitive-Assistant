# Workspaces and Generated Artifacts

CA keeps two kinds of output in two places:

- **Bootstrap artifacts** live in the repo under `workspaces/` and are
  committed (except raw data). The flake ships them.
- **Runtime state** lives under CA home and never enters the repo.

## In the repo: `workspaces/`

```text
workspaces/
  existential/
    data/                                  gitignored
      questions_with_answers_qmd_<ts>.csv  ask-questions
    artifacts/
      human_profile.md                     build-prompts
      profile_candidate_<provider>.md      build-prompts (per-provider drafts)
  operational/
    data/                                  gitignored
      intake/                              raw exports (extract_ai_data.sh)
      ready/<source>/*.jsonl               ingest-corpus
      questions_with_answers_qmd_<ts>.csv  ask-questions
    artifacts/
      human_profile.md, profile_candidate_<provider>.md
      tool_specs/{memory,tasks}.md         build-tool-specs
  skills/<group>/<slug>/SKILL.md           build-skills, imports (see Skills-System.md)
  alignment/artifacts/
    INTERACTION_POSTURE.md, SOUL.md        build-translation-layer
    absorbed.json                          build-translation-layer
    alignment_spec.md                      build-alignment-spec
```

Profile paths come from `LayerProfile` properties in `core/config.py`; the
skill store and alignment paths from `core/paths.py`.

## Outside the repo: CA home

`$CA_HOME`, default `$XDG_DATA_HOME/cognitive-assistant`
(`~/.local/share/cognitive-assistant`). Locations are defined in
`core/paths.py`.

```text
<CA home>/
  improve/                       improvement runtime state (Improvement-Loop.md)
    cursor.json                  processed sessions per harness
    evidence/<session>.json      one analysis per session (with sessionAt)
    open-gaps.json               gaps carried between runs
    ledger.json                  folded/consolidated gap clusters
    experience-context.md        active records rendered for the analysis prompt (rewritten each run)
    proposal.json                latest proposal
    proposals/<id>.json          unapplied proposals that a newer run replaced
    rejections.jsonl             rejected edits (suppresses re-proposals)
    prompts/<run>__<name>.md     every rendered model prompt (+ .json sidecar, 0600)
    model-cache/<sha256>.txt     cached model replies
    journal/                     events.jsonl, current.json, bootstrap.md
    .apply.lock
  experience/
    authored/<id>.md             accepted experience records (the lineage)
    reverted.jsonl               records withdrawn after adoption
  soul/
    compose.json                 deployer prefix/suffix file paths
    generations/NNNN.md, .json   every compiled SOUL and its inputs
    current.md                   symlink to the active generation
    activations.jsonl            when each generation became active
    verdicts.jsonl               outcome verdicts per generation
```

The living SOUL is always built from the bootstrap SOUL at
`workspaces/alignment/artifacts/SOUL.md` (`core/paths.py`
`BOOTSTRAP_SOUL_PATH`): the checkout's copy, or the one inside the installed
`ca` package. There is no override.

## Consumers

The flake exposes the bootstrap artifacts as `lib.artifacts.*`
(see [Nix Packaging](Nix-Packaging-and-Distribution.md)). Hermes reads its
SOUL from `$HERMES_HOME/SOUL.md`, which the Home Manager module links to
`<CA home>/soul/current.md` (see [Living SOUL](Living-SOUL.md)).
