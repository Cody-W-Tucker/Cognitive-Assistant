# Operational Profile

The operational profile extracts grounded workflow patterns from QMD retrieval
over `Base`, `Consulting`, and `Customers`. Its `qmd_query_template.md` directs
the configured direct LLM to produce concrete third-person operational answers
from the bounded passages.

`ingest-corpus` remains available to normalize configured intake exports into
the operational workspace. It does not provide the question-answering retrieval
source. Question answers use `questions_with_answers_qmd_*.csv`, then feed
prompt, skill, and optional tool-spec generation.
