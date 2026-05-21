# Profiles

`profiles/` holds the profile-owned inputs for the pipeline.

The repo is split into two kinds of state:

1. `profiles/<name>/`: committed source material that defines how a profile behaves.
2. `workspaces/<name>/`: generated runtime data and artifacts produced when that profile runs.

`core/config.py` registers each profile as a `LayerProfile` and points the pipeline at the files in this directory. That is how one shared codepath in `core/` can run different workflows for `existential` and `operational` without separate implementations.

## What lives here

Current directories:

- `profiles/existential/`: inputs for the introspective profile.
- `profiles/operational/`: inputs for the work-pattern profile.
- `profiles/alignment/`: prompts for cross-profile artifact verification and SOUL generation.

For the profile-backed layers (`existential` and `operational`), each directory is the durable source of truth for:

- `questions.csv`: the question set the pipeline asks against that profile's evidence source.
- `prompts/`: the prompt templates loaded by `ask-questions`, `build-prompts`, `build-skills`, and `build-tool-specs` when applicable.
- `README.md`: profile-specific notes, intent, and background.

`profiles/operational/scripts/` exists for operational-specific helpers, but the main pipeline still runs through `python -m core`.

## How it connects to the rest of the system

At runtime, `core/config.py` maps each registered profile to:

- a `profile_dir` in `profiles/<name>/`
- a `workspace_dir` in `workspaces/<name>/`
- a `questions_csv` file
- a `prompts_dir`
- pipeline capability flags such as whether the profile supports interview ingest, corpus ingest, or tool spec generation

That profile declaration determines which commands are valid and which artifacts get produced.

Examples:

- `existential` enables `ingest-interview` and includes human answers in `questions.csv` processing.
- `operational` enables `ingest-corpus` and `build-tool-specs`.
- `alignment` is not a normal `--profile` target; it sits above both profiles and consumes their generated outputs.

## Typical flow

The files here are inputs. Running the pipeline turns them into workspace artifacts:

```bash
python -m core --profile existential ask-questions
python -m core --profile existential build-prompts
python -m core --profile existential build-skills

python -m core --profile operational ask-questions
python -m core --profile operational build-prompts
python -m core --profile operational build-skills
python -m core --profile operational build-tool-specs
```

Those commands read from `profiles/<name>/...` and write to `workspaces/<name>/artifacts/...`.

## Editing guidance

Edit files in `profiles/` when you want to change the profile's declared behavior or source prompts.

- Update `questions.csv` to change what the system asks.
- Update `prompts/` to change how the system synthesizes prompts, skills, or tool specs.
- Update `core/config.py` when adding a new profile or changing which prompt files and capabilities a profile exposes.

If you change profile inputs, re-run the relevant `python -m core --profile <name> ...` commands so the corresponding workspace artifacts stay in sync.
