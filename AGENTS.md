# Agent Guidelines for Cognitive-Assistant

Full documentation for the Cognitive-Assistant project is in `docs/`.

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

Profile-specific build commands take `--profile existential|operational`.

```bash
# Shared commands
python -m core list-profiles
python -m core enhance-skill
python -m core build-translation-layer
python -m core build-alignment-spec
python -m core build-agents

# Existential profile workflow
python -m core --profile existential ingest-substrate --graph /path/to/graph.json
python -m core --profile existential ask-questions
python -m core --profile existential build-prompts
python -m core --profile existential build-skills

# Operational profile workflow
python -m core --profile operational ingest-corpus                 # batch
python -m core --profile operational ask-questions
python -m core --profile operational build-prompts
python -m core --profile operational build-skills
python -m core --profile operational build-tool-specs

# Profile-aware validation
python -m core --profile <name> health-check

# Alignment verification
python -m core build-alignment-spec
scripts/verify_alignment.sh --file path/to/artifact.md
```

Subcommands that don't apply to a profile (e.g. `build-tool-specs --profile existential`)
fail with a clear error rather than silently no-op.

`build-skills` writes canonical generated skills to
`workspaces/skills/<profile>/<skill>/SKILL.md` for generated profile skills.
Manual imports can still live under purpose categories like
`workspaces/skills/workflow/<skill>/SKILL.md`.
`build-agents` reads from both profiles, selects roles from the 17-role catalog
at `profiles/alignment/archetypes/` under the policy in
`profiles/alignment/domain_policy.json`, and commits a validated
`agent_plan.json` plus its projections (`persona_map.md` and per-agent soul
documents) to `workspaces/alignment/artifacts/`. `agent_plan.json` commits last
and is authoritative only for that generated bundle.
`build-translation-layer` reads from both profiles and writes the orchestrator
translation layer (`INTERACTION_POSTURE.md` and `SOUL.md`) to
`workspaces/alignment/artifacts/`. It owns `INTERACTION_POSTURE.md`;
`build-agents` only consumes a hash-validated snapshot of it and never
regenerates, repairs, or reconciles it.
`build-alignment-spec` reads both unified skills and agent souls and writes the alignment spec.
`update` runs the full pipeline: per-profile stages (including `build-skills`), then cross-profile
stages (`build-translation-layer` + `build-agents` + `build-alignment-spec`).

See `profiles/alignment/README.md` for details.

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
