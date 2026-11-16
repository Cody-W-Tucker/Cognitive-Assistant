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

## Tests

```bash
nix develop --command python -m unittest discover -s tests -v   # all Python tests
nix develop --command bash -c 'cd improve && npm test'           # Node runtime tests
```

Before presenting results as verified, independently rerun the relevant checks; do not
rely on delegated-worker reports. For repository-wide changes, run both full suites
above; targeted tests do not replace them.

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
**Session source:** The improvement runtime reads harness sessions only from Langfuse
(`LANGFUSE_PUBLIC_KEY` / `_SECRET_KEY` / `_BASE_URL`, `improve/src/langfuse.js`),
never from harness stores on disk; runtime tests use a fake Langfuse
(`improve/tests/fake-langfuse.mjs`, `tests/fixtures.py`). Do not add local
harness-store discovery or readers.
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
