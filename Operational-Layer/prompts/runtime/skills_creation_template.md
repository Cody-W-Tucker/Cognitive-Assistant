<task>
You are generating a small set of OpenCode-compatible skills from an operational user profile.

Your goal is to create narrow, lazily-loaded execution aids that help downstream agents avoid operational misreads and work in the user's preferred way when generic behavior is likely to fail.

These skills should not restate the profile. They should transfer capability.

<input_profile>
{bio_content}
</input_profile>

<skill_specs>
{skill_specs}
</skill_specs>

<core_principles>
1. Skills are conditional tools, not universal instructions.
2. Prefer execution advantages over descriptive restatement.
3. Use the profile as reasoning fuel, not as text to mirror back.
4. Keep each skill narrow and useful mainly in ambiguous or non-trivial work.
5. Encode heuristics, sequencing rules, review logic, failure checks, and escalation patterns.
</core_principles>

<capability_synthesis_method>
For each skill, think through:

1. What is true about how the user works?
2. What generic agent failure does that create risk for?
3. What concrete execution advantage should the skill provide?

Write the skill from step 3.
</capability_synthesis_method>

<content_rules>
Inside each skill:
- include a short `## When To Use` section
- include a short `## Do Not Use` section
- include practical guidance
- prefer “do this when X happens” over “the user is like Y”
- keep the guidance operational and specific
</content_rules>

<output_format>
Return a JSON object and nothing else.

Each key must be a skill directory name. Each value must be the full markdown content for that skill's `SKILL.md` file.
</output_format>
