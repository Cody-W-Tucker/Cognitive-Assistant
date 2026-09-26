# Health Check System

`python -m core --profile <name> health-check` validates:

- Declared prompt files and placeholder rendering.
- Required profile paths and configured direct LLM access.
- QMD command availability.
- Importability of the pipeline modules.

Question answering independently fails closed when QMD retrieval is unavailable,
empty, stale, or has unknown freshness. No LLM call is made in those cases.
