# Agent Guidelines for Cognitive-Assistant

Full documentation for the Cognitive-Assistant project is in `docs/` (index:
`docs/README.md`).

## Layout

The repo is one unified pipeline parameterized by a layer profile.

```
core/                 unified pipeline and CLI (config.py, paths.py, llm.py, stage modules,
                      improve.py / experience.py / living_soul.py / outcome.py / journal.py)
improve/              Node improvement runtime (bin/ca-improve.js, src/, prompts/, tests/)
profiles/<name>/      profile-specific inputs (questions.csv, prompts/)
profiles/alignment/   prompts for the cross-profile stages (not a profile)
workspaces/<name>/    data/ (gitignored) and artifacts/ per profile
workspaces/skills/    the skill store
workspaces/alignment/ bootstrap SOUL, interaction posture, alignment spec
tests/                Python unit tests
```

Two profiles are registered: `existential` and `operational`.

Runtime state (improvement pass, experience records, living SOUL) lives under
CA home (`$CA_HOME`, default `$XDG_DATA_HOME/cognitive-assistant`), never in
the repo. See `docs/Workspaces-and-Generated-Artifacts.md`.

## CLI

Profile-specific build commands take `--profile existential|operational`.

```bash
# Shared commands
python -m core list-profiles
python -m core enhance-skill
python -m core build-translation-layer
python -m core build-alignment-spec

# Existential profile workflow
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

# Everything after ask-questions, for every profile
python -m core update

# Improvement loop and living SOUL (state under CA home)
python -m core improve-run [--headless [--auto]]
python -m core improve-apply [--proposal <id> --decisions "e1=accepted e2=rejected:too-narrow"]
python -m core improve-synthesize
python -m core journal-compact
python -m core soul compile|status|rollback <n>|link <hermes-home>
```

Full flag reference: `docs/CLI-and-Command-Reference.md`.

Subcommands that don't apply to a profile (e.g. `build-tool-specs --profile existential`)
fail with a clear error rather than silently no-op.

`build-skills` writes canonical generated skills to
`workspaces/skills/<profile>/<skill>/SKILL.md` and deletes skills in that
profile folder the profile no longer declares. Manual imports live under
purpose categories like `workspaces/skills/workflow/<skill>/SKILL.md`.
`build-translation-layer` reads from both profiles and writes the orchestrator
translation layer (`INTERACTION_POSTURE.md` and `SOUL.md`, plus
`absorbed.json` naming the lineage records it took in) to
`workspaces/alignment/artifacts/`.
`build-alignment-spec` reads unified skills and writes the alignment spec.
`update` runs `build-prompts`, `build-skills` and (where supported)
`build-tool-specs` for one or all profiles, then the cross-profile stages
(`build-translation-layer` + `build-alignment-spec`). It does not run
`ingest-corpus` or `ask-questions`.

See `profiles/alignment/README.md` and `docs/Alignment-Artifacts.md` for details.

## Tests

```bash
nix develop --command python -m unittest discover -s tests -v   # all Python tests
nix develop --command bash -c 'cd improve && npm test'           # Node runtime tests
```

`tests/` has no `__init__.py`: use `discover -s tests` (not `-t .`), or name
modules directly, e.g. `python -m unittest tests.test_improve`.
`tests/test_ascii.py` enforces strict ASCII on code, root `*.md`, alignment
prompts/artifacts and several `docs/` pages.

## Code Style

**Imports:** Standard library -> third-party -> local. Use absolute imports.

**Type hints:** Required for function parameters and return values.

**Naming:** snake_case for functions/variables, PascalCase for classes,
UPPER_CASE for constants.

**Configuration:** Environment variables for secrets (.env):
`<PROVIDER>_API_KEY` / `_MODEL` / `_MAX_OUTPUT` for bootstrap stages
(`core/llm.py`), `CA_LLM_*` for the improvement runtime (`improve/src/model.js`).
All layer-specific behavior is declared once in `core/config.py` as a
`LayerProfile` and looked up by name; its paths derive from its name. Shared
locations (skill store, alignment artifacts, CA home) are in `core/paths.py`.
Don't add new per-layer scripts; extend a profile.

**Stages:** each stage module exposes `requirements(...)` (a list of missing
configuration) and `async build(...)`; `core/cli.py` runs them through
`_run_stage`.

**Adding a profile:** Add a `LayerProfile(...)` instance in `core/config.py`,
register it via `register_profile`, and create `profiles/<name>/`
(questions.csv, prompts/). `workspaces/<name>/` is created on first write.
See `docs/Layer-Profiles.md`.
