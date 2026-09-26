# Overview

The Cognitive Assistant builds profile artifacts from two QMD-backed layers.

- The existential profile retrieves from `Journal` and `Personal` to synthesize
  reflective first-person answers.
- The operational profile retrieves from `Base`, `Consulting`, and `Customers`
  to synthesize evidence-grounded third-person operational answers.

`ask-questions` fails closed when retrieval is unavailable, empty, stale, or
has unknown freshness. Successful answers are written to
`questions_with_answers_qmd_*.csv`, then `build-prompts` and `build-skills`
produce profile artifacts and canonical skills.
