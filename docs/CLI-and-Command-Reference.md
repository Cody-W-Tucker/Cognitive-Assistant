# CLI And Command Reference

The pipeline is invoked with `python -m core`.

| Command | Scope | Purpose |
| --- | --- | --- |
| `ingest-corpus` | operational | Normalize configured intake exports into ready JSONL packets. |
| `ask-questions` | profile | Retrieve QMD evidence and synthesize answers with the configured direct LLM. |
| `build-prompts` | profile | Build profile artifacts from the latest QMD answer CSV. |
| `build-skills` | profile | Generate canonical skills from `human_profile.md`. |
| `build-tool-specs` | operational | Generate operational tool specifications. |
| `build-translation-layer` | shared | Generate `INTERACTION_POSTURE.md` and `SOUL.md`. |
| `build-alignment-spec` | shared | Generate the alignment specification. |
| `health-check` | profile | Validate prompts, provider configuration, and QMD availability. |

There is no `ingest-substrate` or `verify-alignment` command.
