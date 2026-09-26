# Existential Profile

The existential profile answers reflective questions from bounded QMD retrieval
over `Journal` and `Personal`. Its `qmd_query_template.md` directs the
configured direct LLM to write in the user's reflective voice while keeping
claims proportionate to the retrieved passages.

If QMD cannot provide current, non-empty evidence, the question run fails
without calling the LLM. Successful answers are stored in
`questions_with_answers_qmd_*.csv` and feed profile and skill generation.
