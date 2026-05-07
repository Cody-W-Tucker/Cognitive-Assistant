# Prompts

Runtime prompt templates for the Operational Layer pipeline live in `prompts/`.

- `rlm_query_template.md`: asks RLM to evaluate artifact corpora against the operational taxonomy
- `initial_template.md`: synthesizes the evaluated dataset into `artifacts/human_profile.md`
- `refine_template.md`: transforms the profile into `artifacts/system_prompt.md`
- `skills_creation_template.md`: converts the profile into small, lazily-loaded skills
- `synthesis_prompt.md`: shared evaluation posture used inside the RLM query template
