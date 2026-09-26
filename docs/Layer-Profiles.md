# Layer Profiles

`LayerProfile` declares profile paths, prompts, QMD collections, pipeline
gates, redaction patterns, and skill-generation scope.

| Profile | QMD collections | Ingestion gate |
| --- | --- | --- |
| existential | `Journal`, `Personal` | none |
| operational | `Base`, `Consulting`, `Customers` | `ingest-corpus` |

Both profiles use `qmd_query_template.md` and write
`questions_with_answers_qmd_*.csv` before prompt generation.
