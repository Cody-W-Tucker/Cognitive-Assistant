# Layer Profiles

Everything that differs between layers is declared once, as a `LayerProfile`
in `core/config.py`. Stages take the profile object; there are no per-layer
scripts and no separate config class.

## What a profile declares

| Field | Meaning |
| --- | --- |
| `name` | Profile id; also the directory name under `profiles/`, `workspaces/` and `workspaces/skills/` |
| `display_name` | Human-readable label |
| `qmd_collections` | QMD collections `ask-questions` retrieves from |
| `prompt_files` | Logical prompt name -> file in `profiles/<name>/prompts/` |
| `skill_specs` | `SkillSpec(slug, source_group, source_headings)`: one per generated skill |
| `section_header_template`, `answer_label` | How answers are laid out for `build-prompts` |
| `redaction_patterns` | Regexes replaced with `[REDACTED]` before answers reach `build-prompts` |
| `has_corpus_ingest` | Enables `ingest-corpus` |
| `supported_tools` | Tool spec file -> purpose; enables `build-tool-specs` |

Paths are derived from `name` (properties on `LayerProfile`): `profile_dir`,
`prompts_dir`, `questions_csv`, `workspace_dir`, `data_dir`, `artifacts_dir`,
`human_profile_path`, `tool_specs_dir`. `latest_answers()` returns the newest
`questions_with_answers_qmd_<ts>.csv`; `prompt(name)` loads a declared
template.

## The two profiles

| | existential | operational |
| --- | --- | --- |
| QMD collections | `Journal`, `Personal` | `Base`, `Consulting`, `Customers` |
| Voice | reflective, first person | evidence-grounded, third person |
| Skills | `mode-detection`, `decision-calibration`, `relational-orientation` | `scope-framing`, `failure-recovery`, `complexity-reduction`, `boundary-handoff` |
| Tool specs | none | `memory.md`, `tasks.md` |
| Corpus ingest | no | yes |
| Extra redaction | none | email addresses |

Both profiles share the prompt names `synthesis_prompt`, `initial_template`,
`ensemble_synthesis_template`, `skills_creation_template` and
`qmd_query_template`; operational adds `tool_specs_creation_template` plus the
seed specs `memory.md` and `tasks.md`.

`alignment` is not a profile. `profiles/alignment/` only holds the prompts for
the cross-profile stages; see [Alignment Artifacts](Alignment-Artifacts.md).

## Question answering (`ask-questions`)

Each row of `questions.csv` has `Category`, `Goal`, `Element` and up to three
questions. For every question the stage runs `qmd query --format json` over the
profile's collections (6 results, passages cut to 1200 characters), checks
`qmd status` for the collections and index age, then fills
`qmd_query_template.md` with the cited passages and asks the model for a
one-line answer. Answers land in a new timestamped CSV under
`workspaces/<name>/data/`. Raw notes are never copied into the repo.

## Profile synthesis (`build-prompts`)

The newest answers CSV becomes one markdown document (one section per
category, redaction applied). `initial_template.md` turns it into a draft per
provider, and `ensemble_synthesis_template.md` merges the drafts into
`human_profile.md`. The human profile's level-2 headings are what
`skill_specs` refer to.

## Corpus ingestion (operational)

`ingest-corpus` normalizes raw exports in `workspaces/operational/data/intake/`
into `data/ready/<source>/*.jsonl` and writes a manifest. Recognized inputs
(newest match wins): `opencode_conversations_*.jsonl`,
`cursor_ultimate_*.jsonl`, `open-webui/chat-export-*.json`,
`perplexity/{Search_History,Memory,Conversations}.csv`,
`OpenAI-Chat-export.zip`, `grok_export.zip`.

To fill `intake/` from local coding agents:

```bash
profiles/operational/scripts/extract_ai_data.sh [all|claude-code|codex|cursor|opencode|...]
```

It runs the flake's `ai-data-extractor` package and copies the produced JSONL
into `workspaces/operational/data/intake/`.

`ask-questions` does not read the ready packets; it retrieves from QMD. The
packets are prepared material for indexing and inspection.

## Adding a profile

1. Add a `LayerProfile(...)` in `core/config.py` and call
   `register_profile(...)` on it.
2. Create `profiles/<name>/questions.csv` (same columns as the existing ones)
   and `profiles/<name>/prompts/` with every file named in `prompt_files`.
3. Make sure `skill_specs[*].source_headings` match level-2 headings your
   `initial_template.md` / `ensemble_synthesis_template.md` produce.
4. Run `python -m core --profile <name> health-check`. Workspace directories
   are created on first write.

`build-translation-layer` reads every registered profile's human profile, so a
new profile also feeds the bootstrap SOUL once it has been built.
