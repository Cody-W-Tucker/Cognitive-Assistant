<task>
You are generating a small set of OpenCode-compatible skills from a human-readable user profile.

Your goal is not to produce a fixed menu of skill types. Your goal is to discover which few skills would create the largest practical reasoning advantage for future agents working with this user.

These skills should emerge from what is most consequential in the profile: recurring interpretive misreads, decision traps, calibration failures, constraint blindspots, strategic translation gaps, tone mismatches, or any other repeated pressure point that materially changes the right response.

The generated skills should not merely restate or segment the profile. They should transform the profile into operational capabilities that give downstream agents better judgment, sharper intervention patterns, and more effective action under ambiguity. The goal is not profile dissemination. The goal is capability transfer.

A good skill is not a topic bucket. It is a reusable reasoning advantage derived from the user.

<input_profile>
{bio_content}
</input_profile>

<core_principles>
1. Skills are exception-handling context, not baseline instructions for every interaction.
2. Discover the skills from the profile's highest-leverage pressure points; do not force the profile into preselected skill categories.
3. Use profile insights primarily as background reasoning fuel, not as user-facing psychologizing.
4. Do not produce mirror language that explains the user back to themselves unless the request explicitly calls for that.
5. Keep each skill narrow. The agent should not feel compelled to load it for straightforward factual, coding, formatting, or procedural requests.
6. Each skill must encode what a downstream AI can now do better, not just what is true about the user.
7. Prefer heuristics, intervention logic, decision rules, test patterns, framing moves, and failure-mode interrupts over descriptive restatement.
</core_principles>

<capability_synthesis_method>
First decide whether a skill should exist at all. A pattern deserves a skill only if it meets most of these tests:

- generic model behavior is likely to misread or mishandle it
- the pattern recurs across multiple contexts or has high cost when missed
- the skill would noticeably improve judgment, interpretation, prioritization, or collaboration
- the advantage cannot be captured well enough by baseline instructions alone

Then, for each skill, do this synthesis internally before writing:

1. **Profile truth**: What is true about the user from the profile?
2. **Misread risk**: What generic model failure does that create risk for?
3. **Capability gain**: What concrete reasoning or intervention advantage should the assistant gain?
4. **Activation condition**: In what situations should this skill actually be loaded?

Write the skill from steps 3 and 4, not from step 1.

Examples:
- Bad: "A skill about ambiguity."
- Better: "Use when the surface request is underdetermined and generic advice would likely solve the wrong problem; reconstruct the user's actual concern before proposing action."

- Bad: "A skill about strategic planning."
- Better: "Use when the user faces multiple viable paths and the real need is not a plan but a reversibility-aware decision process with proof thresholds and live tests."

- Bad: "A skill about tone."
- Better: "Use when a generic supportive answer would sound reductive or patronizing; calibrate for peer-level engagement, directness, and useful challenge."
</capability_synthesis_method>

<selection_rules>
- Do not assume the final set must cover every major section of the profile.
- Do not create one skill per theme by default.
- It is better to produce 2-5 highly leveraged skills than a larger set of thin or redundant ones.
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
- "Use when the user's request is ambiguous, unusually strategic, or likely to be misread by generic advice."
- "Use when the answer depends on deeper priorities or constraints that should guide reasoning quietly in the background."

Descriptions should NOT sound like:
- "Core instructions for responding to this user."
- "Always load before answering."
- "Required response style for all interactions."
</description_rules>

<content_rules>
Inside each skill:
- include a short `## When To Use` section
- include a short `## Do Not Use` section
- provide concise capability guidance
- include the specific failure this skill prevents
- avoid duplicating the entire profile
- avoid excessive repetition of user-specific vocabulary
- avoid explicit references to wounds, archetypes, or psychologizing labels unless absolutely necessary for decision quality
- avoid section-by-section paraphrase of the profile
- prefer "do this when X happens" over "the user is like Y"
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
4. When should the skill stay unloaded?
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
1. Each skill exists because it creates a real capability advantage, not because it matches a familiar category.
2. Each description is conditional, not mandatory.
3. The final set is small, high-leverage, and non-redundant.
4. Straightforward requests should not require loading any of these skills.
5. After reading a skill, a downstream AI should know what it can do better, not just know more about the user.
6. The set reflects what is most relevant in this specific profile, even if that produces an unusual mix of skills.
</quality_bar>
</task>
