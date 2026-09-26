# Glossary

- **QMD**: Local markdown retrieval CLI used before question synthesis.
- **Direct LLM**: The configured provider client used to synthesize an answer
  from current QMD passages.
- **Existential profile**: The profile that retrieves from `Journal` and
  `Personal`.
- **Operational profile**: The profile that retrieves from `Base`, `Consulting`,
  and `Customers`, and may normalize intake with `ingest-corpus`.
- **QMD answer CSV**: A timestamped
  `questions_with_answers_qmd_<timestamp>.csv` file containing `AI_Answer`
  columns for downstream prompt generation.
- **Alignment spec**: The generated verification specification at
  `workspaces/alignment/artifacts/alignment_spec.md`.
