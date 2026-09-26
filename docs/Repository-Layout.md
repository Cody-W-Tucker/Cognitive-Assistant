# Repository Layout

```text
core/                 Profile-aware pipeline commands
profiles/<name>/      Questions and QMD synthesis prompts
workspaces/<name>/    Runtime data and generated artifacts
lib/                  Shared configuration, LLM, prompt, and health helpers
tests/                Unit tests, including fake QMD and LLM boundaries
```

Each profile prompt directory contains `qmd_query_template.md`. QMD answer
files use `questions_with_answers_qmd_*.csv`. The operational profile retains
`ingest-corpus`; no schema-substrate ingestion path exists.
