# Agent Guidelines for Cognitive-Assistant

## Layout

The repo is one unified pipeline parameterized by a layer profile.

```
core/                 unified pipeline (one set of scripts)
profiles/<name>/      profile-specific inputs (questions.csv, prompts/)
workspaces/<name>/    runtime data (data/, artifacts/) per profile
lib/                  shared infrastructure (config, llm, prompts, health)
scripts/              shell launchers and utility entry points
tests/                profile-aware health tests
```

Two profiles are registered: `existential` and `operational`.

## CLI

All commands take `--profile existential|operational`.

```bash
python -m core list-profiles
python -m core --profile <name> health-check

# Existential profile workflow
python -m core --profile existential ingest-interview              # interactive
python -m core --profile existential ask-questions                 # human-seeded
python -m core --profile existential ask-questions --filesystem-only
python -m core --profile existential build-prompts
python -m core --profile existential build-skills

# Operational profile workflow
python -m core --profile operational ingest-corpus                 # batch
python -m core --profile operational ask-questions
python -m core --profile operational build-prompts
python -m core --profile operational build-skills
python -m core --profile operational build-tool-specs

# Alignment (cross-profile, no --profile flag)
python -m core build-alignment-spec
scripts/verify_alignment.sh --file path/to/artifact.md
```

Subcommands that don't apply to a profile (e.g. `build-tool-specs --profile existential`)
fail with a clear error rather than silently no-op.

`build-alignment-spec` reads from both profiles and writes
`workspaces/alignment/artifacts/alignment_spec.md`. Regenerate it after `build-skills`
runs for either profile. See `profiles/alignment/README.md` for details.

## Tests

```bash
nix develop --command python -m unittest tests.test_health -v
```

The health test runs `check_prompt_files` and `check_prompt_rendering` against
every registered profile.

## Code Style

**Imports:** Standard library -> third-party -> local. Use absolute imports.

**Type hints:** Required for function parameters and return values.

**Naming:** snake_case for functions/variables, PascalCase for classes,
UPPER_CASE for constants.

**Configuration:** Environment variables for secrets (.env). All layer-specific
behavior is declared once in `core/config.py` as a `LayerProfile` and looked up
by name. Don't add new per-layer scripts; extend a profile.

**Adding a profile:** Add a `LayerProfile(...)` instance in `core/config.py`,
register it via `register_profile`, create the matching `profiles/<name>/`
(questions.csv, prompts/) and `workspaces/<name>/` directories.
