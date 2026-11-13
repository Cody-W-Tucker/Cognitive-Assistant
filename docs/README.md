# Cognitive Assistant documentation

Start with the Overview, then Getting Started. Each topic has one page.

| Page | What it covers |
| --- | --- |
| [Overview](Overview.md) | What CA builds, the bootstrap/runtime split, repository layout, glossary |
| [Getting Started](Getting-Started.md) | Dev shell, model configuration, first build, health check, running the tests |
| [CLI and Command Reference](CLI-and-Command-Reference.md) | Every `python -m core` command: flags, inputs, outputs |
| [Layer Profiles](Layer-Profiles.md) | `LayerProfile`, the existential and operational profiles, corpus ingestion, question answering, adding a profile |
| [Skills System](Skills-System.md) | The skill store, `build-skills`, `enhance-skill`, imported skills |
| [Alignment Artifacts](Alignment-Artifacts.md) | Bootstrap SOUL, interaction posture, `absorbed.json`, alignment spec |
| [Workspaces and Generated Artifacts](Workspaces-and-Generated-Artifacts.md) | Where every file lives: repo workspaces and CA home runtime state |
| [Improvement Loop](Improvement-Loop.md) | `improve-run` / `improve-apply` / `improve-synthesize`, the Node runtime, the journal |
| [Living SOUL](Living-SOUL.md) | Generations, outcome check, auto adopt/revert, rebootstrap, Home Manager wiring |
| [Nix Packaging and Distribution](Nix-Packaging-and-Distribution.md) | Flake packages, modules, `lib.artifacts`, dev shell |
| [Projection Experiments](Projection-Experiments.md) | Langfuse review queue and A/B experiment workflow |

Related READMEs outside `docs/`: `profiles/README.md`,
`profiles/alignment/README.md`, `workspaces/skills/README.md`.
