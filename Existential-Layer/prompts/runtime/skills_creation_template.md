<task>
You are generating a small set of OpenCode-compatible skills from a human-readable user profile.

Your goal is not to produce a mirror of the user's psychology. Your goal is to create narrow, lazily-loaded reasoning aids that downstream AI agents can load only when generic model behavior is likely to misread the user or fail in a novel, high-context, or tradeoff-heavy interaction.

<input_profile>
{bio_content}
</input_profile>

<skill_specs>
{skill_specs}
</skill_specs>

<core_principles>
1. Skills are exception-handling context, not baseline instructions for every interaction.
2. Use profile insights primarily as background reasoning fuel, not as user-facing psychologizing.
3. Do not produce “mirror” language that explains the user back to themselves unless the request explicitly calls for that.
4. Prefer better judgment, interpretation, prioritization, and collaboration over therapeutic reflection.
5. Keep each skill narrow. The agent should not feel compelled to load it for straightforward factual, coding, formatting, or procedural requests.
</core_principles>

<description_rules>
Each skill description must:
- clearly signal conditional use
- say when the skill helps
- imply when it is not needed
- avoid sounding universal or mandatory

Descriptions should sound like:
- “Use when the user’s request is ambiguous, unusually strategic, or likely to be misread by generic advice.”

Descriptions should NOT sound like:
- “Core instructions for responding to this user.”
- “Always load before answering.”
- “Required response style for all interactions.”
</description_rules>

<content_rules>
Inside each skill:
- include a short “When To Use” section
- include a short “Do Not Use” section
- provide concise reasoning guidance
- avoid duplicating the entire profile
- avoid excessive repetition of user-specific vocabulary
- avoid explicit references to “wounds,” “archetypes,” or psychologizing labels unless absolutely necessary for decision quality
</content_rules>

<output_format>
Return a JSON object and nothing else.

Each key must be a skill directory name. Each value must be the full markdown content for that skill's SKILL.md file.

Example shape:
{{
  "example-skill": "---\nname: example-skill\ndescription: Use when ...\ncompatibility: opencode\n---\n## When To Use\n..."
}}
</output_format>

<quality_bar>
Before producing the final JSON, verify:
1. Each frontmatter name matches its directory key exactly.
2. Each description is conditional, not mandatory.
3. Each skill is useful mainly for ambiguous, novel, high-context, or strategically loaded requests.
4. Straightforward requests should not require loading any of these skills.
5. The skills act like cognitive-partner aids, not reflective mirrors.
</quality_bar>
</task>
