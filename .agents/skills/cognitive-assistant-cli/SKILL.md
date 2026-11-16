---
name: cognitive-assistant-cli
description: Use when running or changing Cognitive-Assistant CLI commands, profile builds, skill generation, or alignment stages.
user-invocable: false
metadata:
  internal: true
---

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
python -m core improve-outcome [--since 70d --dry-run]   # score outcomes; dry run is the backtest
python -m core improve-apply [--proposal <id> --decisions "e1=accepted e2=rejected:too-narrow"]
python -m core improve-synthesize
python -m core journal-compact
python -m core review-queue [--dry-run]                  # refill the Langfuse review queue
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
