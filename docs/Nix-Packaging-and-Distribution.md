# Nix Packaging and Distribution

Everything is in `flake.nix`.

## Packages

| Package | What it is |
| --- | --- |
| `ca` | The CLI (`python -m core`) with Python and Node.js on its path, so `ca improve-run` can launch the improvement runtime. Carries the repo, including the bootstrap SOUL |
| `langfuse-review-queue` | `python -m core.langfuse_review`; also `default` |
| `ai-data-extractor` | Re-export of `github:Cody-W-Tucker/ai-data-extraction`, used by `profiles/operational/scripts/extract_ai_data.sh` |

The `ca` package's Python has only `python-dotenv`: enough for the improvement
loop and `soul` commands. Bootstrap stages that call providers need the dev
shell.

## Modules

**`homeManagerModules.cognitive-assistant`** (`services.cognitive-assistant`)
runs the living SOUL as the same user as Hermes. On activation it runs
`ca soul compile` with the configured `soul.prefix` / `soul.suffix` and
`ca soul link <hermesHome>`; with `improve.enable` (default) it adds a weekly
`ca-improve` user service/timer that runs `ca improve-run --headless`, plus
`--auto --min-sessions <n>` when `improve.auto` (default) and one `--harness`
per entry of `improve.harnesses` (default `[ "hermes" ]`). The model endpoint
comes from `llm.baseUrl`, `llm.model`, `llm.roleModels` and `llm.apiKeyFile`,
exported as the `CA_LLM_*` variables. `hermesHome` is required and its
`SOUL.md` must not also be declared in `hermesHomeFiles`. Example and
semantics: [Living SOUL](Living-SOUL.md).

**`nixosModules.langfuse-review-queue`** (`services.langfuse-review-queue`)
installs a daily oneshot service and timer that refills the Langfuse review
queue, with `baseUrl`, `environmentFile` (credentials) and `timerConfig`
options. See [Projection Experiments](Projection-Experiments.md).

## `lib.artifacts`

Committed bootstrap artifacts for downstream flakes:

| Attribute | Value |
| --- | --- |
| `lib.artifacts.skills.names` | Every skill slug in the store |
| `lib.artifacts.skills.files.<slug>` | That skill's `SKILL.md` content |
| `lib.artifacts.skills.categorized` | The `workspaces/skills` tree (`<group>/<slug>/SKILL.md`) |
| `lib.artifacts.alignment.spec` | `alignment_spec.md` |
| `lib.artifacts.alignment.translationLayer` | Bootstrap `SOUL.md` |
| `lib.artifacts.alignment.interactionPosture` | `INTERACTION_POSTURE.md` |
| `lib.artifacts.{existential,operational}.humanProfile` | Each layer's `human_profile.md` |
| `lib.artifacts.operational.toolSpecs.{memory,tasks}` | Operational tool specs |

Hermes should take its SOUL from the living SOUL (Home Manager module), not
from `translationLayer`, once the module is enabled.

## Dev shell

`nix develop` provides Python 3.14 with `anthropic`, `openai`, `pandas`,
`pydantic` and `python-dotenv`; QMD from `llm-agents.nix` (Vulkan and CUDA
disabled); Node.js; and `ai-data-extractor`.
