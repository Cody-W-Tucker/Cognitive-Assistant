# Core Pipeline Architecture

The CLI resolves a `LayerProfile` and runs the corresponding stage.

1. Operational sources can be normalized by `ingest-corpus`.
2. `ask-questions` retrieves QMD passages for the profile's declared
   collections.
3. A configured direct LLM synthesizes answers only after valid, current
   retrieval succeeds.
4. `build-prompts`, `build-skills`, and optional operational tool-spec
   generation build downstream artifacts.
5. Cross-profile stages generate the translation layer and alignment spec.

There is no RLM execution, schema graph ingestion, or standalone verifier.
