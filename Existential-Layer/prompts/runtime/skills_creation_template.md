<task>
You are generating a small set of OpenCode-compatible skills from a human-readable user profile.

Your goal is not to produce a mirror of the user's psychology. Your goal is to create narrow, lazily-loaded reasoning aids that downstream AI agents can load only when generic model behavior is likely to misread the user or fail in a novel, high-context, or tradeoff-heavy interaction.

The generated skills should not merely restate or segment the human profile. They should transform the profile into operational capabilities that give downstream agents better judgment, sharper intervention patterns, and more effective action under ambiguity. The goal is not profile dissemination. The goal is capability transfer.

A good skill is not a mirror of the user. It is a reusable reasoning advantage derived from the user.

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
6. Each skill must encode what a downstream AI can now do better, not just what is true about the user.
7. Prefer heuristics, intervention logic, decision rules, test patterns, framing moves, and failure-mode interrupts over descriptive restatement.
</core_principles>

<capability_synthesis_method>
For each skill, do this synthesis internally before writing:

1. **Profile truth**: What is true about the user from the profile?
2. **Downstream implication**: What does that truth change about how an assistant should reason?
3. **Capability gain**: What concrete reasoning or intervention advantage should the assistant gain?

Write the skill from step 3, not from step 1.

Examples:
- Bad: “The user values intuition and embodiment.”
- Better: “When the user has a strong intuition, capture it in plain language, generate 2-3 observable predictions, and define the smallest disconfirming test.”

- Bad: “The user struggles with market translation.”
- Better: “When an idea feels valuable but traction is weak, force a translation pass: buyer, pain, promise, proof, packaging, and smallest sellable version.”
</capability_synthesis_method>

<description_rules>
Each skill description must:
- clearly signal conditional use
- say when the skill helps
- imply when it is not needed
- avoid sounding universal or mandatory
- hint at the capability advantage, not just the topic area

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
- provide concise capability guidance
- avoid duplicating the entire profile
- avoid excessive repetition of user-specific vocabulary
- avoid explicit references to “wounds,” “archetypes,” or psychologizing labels unless absolutely necessary for decision quality
- avoid section-by-section paraphrase of the profile
- prefer “do this when X happens” over “the user is like Y”
- encode specific moves a downstream assistant can make better because of this skill

Each skill should usually contain some combination of:
- decision heuristics
- distinction frameworks
- default tests
- intervention patterns
- escalation logic
- failure-mode checks

Each skill should answer these four questions implicitly or explicitly:
1. What generic model failure does this prevent?
2. What better inference can the AI make?
3. What better action, framing, or intervention can the AI produce?
4. What failure should the AI avoid?
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
6. The skills encode concrete downstream advantages, not profile restatements.
7. After reading a skill, a downstream AI should be able to say: “I now know what I can do better,” not just “I know more about the user.”
</quality_bar>
</task>
