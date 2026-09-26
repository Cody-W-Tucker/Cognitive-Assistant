# Configuration System

`core.config.LayerProfile` is the single declaration point for profile-specific
paths, prompt files, QMD collections, redaction patterns, and pipeline gates.

The existential profile declares `Journal` and `Personal`. The operational
profile declares `Base`, `Consulting`, and `Customers`, enables `ingest-corpus`,
and supports tool-spec generation.

`Config` provides profile paths, CSV schema, prompt loading, redaction, and
direct-LLM validation. Its output pattern is
`questions_with_answers_qmd_{timestamp}.csv`.
