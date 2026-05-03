<task>
You are generating a small set of OpenCode-compatible skills from a tacit work profile.

Your goal is not to produce a fixed menu of skill types. Your goal is to discover which few skills would create the largest practical advantage for future agents working with this user.

These skills should emerge from what is most consequential in the profile: recurring misreads, sequence violations, truth-contact failures, breakdown patterns, compression opportunities, handoff risks, operator-burden issues, or any other repeated pressure point that materially changes the right response.

These skills should not restate the profile. They should transfer capability.

A good skill is not a topic bucket. It is a reusable reasoning or execution advantage derived from the user's real work logic.

<input_profile>
{bio_content}
</input_profile>

<core_principles>
1. Skills are conditional tools, not universal instructions.
2. Discover the skills from the profile's highest-leverage pressure points; do not force the profile into preselected skill categories.
3. Use the profile as reasoning fuel, not as text to mirror back.
4. Keep each skill narrow and useful mainly in ambiguous or non-trivial work.
5. Prefer execution advantages over descriptive restatement.
6. Encode heuristics, sequencing rules, review logic, failure checks, escalation patterns, distinction frameworks, repair moves, or interpretation aids when those are the real advantage.
7. Straightforward factual, coding, formatting, or procedural requests should not require loading these skills.
</core_principles>

<capability_synthesis_method>
First decide whether a skill should exist at all. A pattern deserves a skill only if it meets most of these tests:

- generic model behavior is likely to misread or mishandle it
- the pattern recurs across multiple contexts or has high cost when missed
- the skill would noticeably improve judgment, sequencing, verification, or handoff quality
- the advantage cannot be captured well enough by baseline instructions alone

Then, for each skill, think through:

1. **Profile truth**: What is true about how the user works?
2. **Misread risk**: What generic agent failure does that create risk for?
3. **Capability gain**: What concrete reasoning or execution advantage should the skill provide?
4. **Activation condition**: In what situations should this skill actually be loaded?

Write the skill from steps 3 and 4, not from step 1.

Examples:
- Bad: "A skill about simplification."
- Better: "Use when the response risks becoming structurally heavier than the job; collapse layers until each surviving piece has visible operational payoff."

- Bad: "A skill about artifact inspection."
- Better: "Use when recommendations could outrun proof; force direct contact with the artifact, bound claims to inspected evidence, and prefer reversible probes when context is incomplete."

- Bad: "A skill about workflow."
- Better: "Use when the answer could violate sequence integrity; determine whether the user needs orientation, fit judgment, execution, diagnosis, refinement, or handoff preparation before choosing response shape."
</capability_synthesis_method>

<selection_rules>
- Do not assume the final set must cover every major section of the profile.
- Do not create one skill per theme by default.
- It is better to produce 2-4 highly leveraged skills than a larger set of thin or redundant ones.
- Merge overlapping skills unless separate activation conditions create clearly different advantages.
- If the profile supports an unusual but important skill shape, prefer that over familiar categories.
</selection_rules>

<description_rules>
Each skill description must:
- clearly signal conditional use
- say when the skill helps
- imply when it is not needed
- avoid sounding universal or mandatory
- hint at the capability advantage, not just the topic area

Descriptions should sound like:
- "Use when the response risks drifting away from the real artifact or outrunning its proof base."
- "Use when the task is directionally right but still too expensive for the next operator to use or maintain."

Descriptions should NOT sound like:
- "Core instructions for responding to this user."
- "Always load before answering."
- "Required style guide for all work."
</description_rules>

<content_rules>
Inside each skill:
- include a short `## When To Use` section
- include a short `## Do Not Use` section
- include practical guidance
- include the specific failure this skill prevents
- prefer "do this when X happens" over "the user is like Y"
- keep the guidance operational and specific
- avoid duplicating the entire profile
- avoid creating a generic assistant style guide

Each skill should usually contain some combination of:
- decision heuristics
- sequence checks
- truth-contact tests
- compression rules
- handoff checks
- repair patterns
- failure-mode interrupts
- verification defaults

Each skill should answer these questions implicitly or explicitly:
1. What generic model failure does this prevent?
2. What better inference can the agent now make?
3. What better action, framing, or intervention can the agent now produce?
4. When should the skill stay unloaded?
</content_rules>

<output_format>
Return a JSON object and nothing else.

Each key must be a skill directory name. Each value must be the full markdown content for that skill's `SKILL.md` file.

Example shape:
{{
  "example-skill": "---\nname: example-skill\ndescription: Use when ...\ncompatibility: opencode\n---\n## When To Use\n..."
}}
</output_format>

<quality_bar>
Before producing the final JSON, verify:
1. Each skill exists because it creates a real capability advantage, not because it matches a familiar category.
2. Each description is conditional, not mandatory.
3. The final set is small, high-leverage, and non-redundant.
4. Straightforward requests should not require loading any of these skills.
5. After reading a skill, a downstream agent should know what it can do better, not just know more about the user.
6. The set reflects what is most relevant in this specific profile, even if that produces an unusual mix of skills.
</quality_bar>
</task>
