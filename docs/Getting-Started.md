# Getting Started

## Dev shell

```bash
nix develop
```

Run every command below from the repo root inside this shell. For its
packages and dependencies, see [Nix Packaging](Nix-Packaging-and-Distribution.md#dev-shell).

## Model configuration (bootstrap stages)

Bootstrap stages call models through `core/llm.py` (`complete()`: one prompt
in, one text reply out). Configuration comes from the environment; a `.env`
file in the working directory is loaded automatically.

| Variable | Meaning |
| --- | --- |
| `<PROVIDER>_API_KEY` | Required for each provider a stage uses |
| `<PROVIDER>_MODEL` | Model override (defaults are in `core/llm.py`) |
| `<PROVIDER>_MAX_OUTPUT` | Max output tokens (default 128000) |

`<PROVIDER>` is `ANTHROPIC`, `OPENAI` or `XAI`. Anthropic is the default
provider for every stage. `build-prompts` additionally drafts with xAI and
OpenAI, so it needs all three keys; so does `health-check`.

The improvement runtime does not use these variables. It talks to one
OpenAI-compatible endpoint configured with `CA_LLM_*` variables; see
[Improvement Loop](Improvement-Loop.md).

## First build

```bash
python -m core list-profiles
python -m core --profile existential health-check
python -m core --profile existential ask-questions
python -m core --profile existential build-prompts
python -m core --profile operational ask-questions
python -m core --profile operational build-prompts
python -m core update          # skills, tool specs, translation layer, alignment spec
```

Each stage checks its requirements first (API keys, input files) and exits 1
with a list of what is missing before making any model call. See the
[CLI reference](CLI-and-Command-Reference.md) for every command.

## Health check

`python -m core --profile <name> health-check` makes no model call. It checks:

- every prompt template the profile declares, plus the alignment prompts,
  exists, is non-empty and parses as a `str.format` template with keyword
  placeholders only;
- the profile's `questions.csv` exists and it declares QMD collections;
- every stage module imports;
- all three provider API keys are set and the `anthropic` / `openai` packages
  import;
- `qmd` is on `PATH`.

## Tests

Python (stdlib `unittest`; no network, models or QMD are faked):

```bash
nix develop --command python -m unittest discover -s tests -v
```

`tests/` has no `__init__.py`, so pass `-s tests` without `-t .` (with `-t .`
discovery fails with "Start directory is not importable"). A single module runs
as `python -m unittest tests.test_improve`.

| Module | Covers |
| --- | --- |
| `tests/test_bootstrap.py` | prompt creation, question asking, skills, tool specs, translation layer, alignment spec, `core/llm.py`, prompt template health |
| `tests/test_improve.py` | `improve-run` (mock analyzer over fixture sessions), `improve-synthesize`, decision parsing, `improve-apply` |
| `tests/test_living_soul.py` | generations, rollback, absorbed records, linking |
| `tests/test_outcome.py` | miss rate, z-test, `--auto` cycle |
| `tests/test_journal.py` | journal sanitization, concurrent appends, compaction |
| `tests/test_langfuse_review.py` | review queue selection |
| `tests/test_ascii.py` | strict ASCII for code, root `*.md`, alignment prompts/artifacts and selected docs |

Tests run against a temporary CA home (`CA_HOME`) and a temporary bootstrap
SOUL (`paths.BOOTSTRAP_SOUL_PATH` patched by `tests/fixtures.py`), never your
real state.

Node (the improvement runtime, `node:test`):

```bash
nix develop --command bash -c 'cd improve && npm test'
# or without the dev shell:
cd improve && nix shell nixpkgs#nodejs --command node --test tests/*.test.mjs
```
