# Prompts

Prompt templates for the Operational Layer pipeline. The logical names are declared in `core/config.py` (`OPERATIONAL_PROFILE.prompt_files`).

- `qmd_query_template.md`: asks the direct LLM to evaluate QMD-retrieved artifact passages against the operational taxonomy
- `initial_template.md`: drafts the human profile from the answered questions (one draft per provider)
- `skills_creation_template.md`: converts the profile into small, lazily-loaded skills
- `synthesis_prompt.md`: shared evaluation posture used inside the QMD query template
- `ensemble_synthesis_template.md`: merges the per-provider profile drafts into `human_profile.md`
- `tool_specs_creation_template.md`: generates `artifacts/tool_specs/*.md` from the profile
- `memory.md`, `tasks.md`: seed exemplars for the two tool specs
