# Question Answering And Prompt Creation

`ask-questions` retrieves bounded QMD passages and synthesizes each answer with
the configured direct LLM client. The LLM is not called when retrieval is
unavailable, empty, stale, or lacks freshness information.

Each profile uses a `qmd_query_template.md` prompt. Existential retrieval uses
`Journal` and `Personal`; operational retrieval uses `Base`, `Consulting`, and
`Customers`. The prompt receives cited passages for grounding, while final
answers omit source labels and paths.

Answers are written as `questions_with_answers_qmd_<timestamp>.csv` with the
existing `AI_Answer` columns. `build-prompts` reads the most recent file using
that pattern and produces the profile artifacts.
