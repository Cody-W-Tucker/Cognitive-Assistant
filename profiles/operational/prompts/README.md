# Prompts

Runtime prompt templates for the Operational Layer pipeline live in `prompts/`.

- `qmd_query_template.md`: asks the direct LLM to evaluate QMD-retrieved artifact passages against the operational taxonomy
- `initial_template.md`: synthesizes the evaluated dataset into `artifacts/human_profile.md`
- `skills_creation_template.md`: converts the profile into small, lazily-loaded skills
- `synthesis_prompt.md`: shared evaluation posture used inside the QMD query template
