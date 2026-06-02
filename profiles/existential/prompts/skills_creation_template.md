<task>
You are generating OpenCode-compatible skills from grouped sections of a human-readable user profile.

Your goal is not to produce a fixed menu of skill types. Your goal is to preserve the highest-leverage reasoning advantages in each heading group. Some groups may deserve one skill; some may deserve two if they contain clearly different activation conditions.

These skills should emerge from what is most consequential in each group: recurring interpretive misreads, decision traps, calibration failures, constraint blindspots, strategic translation gaps, tone mismatches, or any other repeated pressure point that materially changes the right response.

The generated skills should not merely restate or segment the profile. They should transform the profile into operational capabilities that give downstream agents better judgment, sharper intervention patterns, and more effective action under ambiguity. The goal is not profile dissemination. The goal is capability transfer.

A good skill is not a topic bucket. It is a reusable reasoning advantage derived from the user.

<input_profile_groups>
{grouped_bio_content}
</input_profile_groups>

<core_principles>
1. Skills are exception-handling context, not baseline instructions for every interaction.
2. Discover the skills from the profile's highest-leverage pressure points; do not force the profile into preselected skill categories.
3. Use profile insights primarily as background reasoning fuel, not as user-facing psychologizing.
4. Do not produce mirror language that explains the user back to themselves unless the request explicitly calls for that.
5. Keep each skill narrow. The agent should not feel compelled to load it for straightforward factual, coding, formatting, or procedural requests.
6. Each skill must encode what a downstream AI can now do better, not just what is true about the user.
7. Prefer heuristics, intervention logic, decision rules, test patterns, framing moves, and failure-mode interrupts over descriptive restatement.
</core_principles>

<forecasting_objective>
Use the profile to extract the reasoning advantages that the old system-prompt path was meant to preserve. The skill set should collectively improve three forecasting tasks:

1. Intention forecasting
   - Reconstruct the path that likely led to the request.
   - Identify the real problem under the surface wording.
   - Notice what may have triggered the question now.
   - When useful, map the sequence: experience -> heuristic -> action -> reconceptualization.

2. Attention forecasting
   - Notice the small set of signals that predict most of this user's priorities.
   - Catch the details this user cares about that a generic model would miss.
   - Distinguish what they notice early from what they may be underweighting.

3. Outcome forecasting
   - Predict what this user will count as a good response.
   - Make their implicit evaluation criteria explicit.
   - Help the model tell the difference between "this gets me" and "this missed the point."
</forecasting_objective>

<transformation_principles>
- Every skill should improve at least one of the three forecasting tasks.
- Focus on where this user differs from the default user profile.
- Keep contradictions and tensions intact instead of smoothing them out.
- Include both what keeps showing up and what is strangely absent when that changes how an agent should reason.
- Anchor the skill set in observable patterns, not flattering abstractions.
- Use plain language. Avoid padded, promotional, or generic model-sounding phrasing.
</transformation_principles>

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
5. **Forecasting win**: Does this skill mainly improve intention forecasting, attention forecasting, outcome forecasting, or a real combination?

Write the skill from steps 3-5, not from step 1.

Examples:
- Bad: "A skill about ambiguity."
- Better: "Use when the surface request is underdetermined and generic advice would likely solve the wrong problem; reconstruct the user's actual concern before proposing action."

- Bad: "A skill about strategic planning."
- Better: "Use when the user faces multiple viable paths and the real need is not a plan but a reversibility-aware decision process with proof thresholds and live tests."

- Bad: "A skill about tone."
- Better: "Use when a generic supportive answer would sound reductive or patronizing; calibrate for peer-level engagement, directness, and useful challenge."
</capability_synthesis_method>

<selection_rules>
- Produce at least one skill for every provided `<skill_group>`.
- A group may produce multiple skills only when the activation conditions are clearly different and merging them would create a blurry or over-broad skill.
- Each skill should synthesize across the sections inside its group, not paraphrase them one by one.
- Preserve the strongest capability advantage in the group even if some source material stays implicit.
- Keep overlap low across the final set by choosing the most distinctive activation condition for each group.
- If a group supports an unusual but important skill shape, prefer that over familiar categories.
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
- avoid semantic mimicry that turns the user's language into a performative lexicon
- avoid explicit references to wounds, archetypes, or psychologizing labels unless absolutely necessary for decision quality
- avoid section-by-section paraphrase of the profile
- prefer "do this when X happens" over "the user is like Y"
- encode specific moves a downstream assistant can make better because of this skill
- preserve interpretive rules more than signature terms

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

<set_composition_rules>
Across the final set, try to preserve the highest-value material that would otherwise have gone into:

- intention patterns: recurring reasons the user asks what they ask
- signal dictionary: terms, absences, and emphasis shifts that need correct interpretation
- success criteria: what this user counts as a good answer versus a miss
- operational defaults: where directness, challenge, structure, and anti-pattern avoidance materially change fit

Do not turn these into rigid skill categories. Use them as compression targets inside the fixed group structure.
</set_composition_rules>

<output_format>
Return a JSON object and nothing else.

Each key must be a skill directory name. Each value must be the full markdown content for that skill's SKILL.md file.

Return at least one skill for each provided `<skill_group>`.

Every skill must include `source_group: group-name` in frontmatter, where `group-name` exactly matches the `<skill_group name="...">` it came from.

Example shape:
{{
  "example-skill": "---\nname: example-skill\ndescription: Use when ...\nsource_group: group-1\ncompatibility: opencode\n---\n## When To Use\n..."
}}
</output_format>

<quality_bar>
Before producing the final JSON, verify:
1. Each skill exists because it creates a real capability advantage, not because it matches a familiar category.
2. Each description is conditional, not mandatory.
3. The final set covers every input group, stays high-leverage, and only uses multiple skills from the same group when that prevents a blurry merged skill.
4. Straightforward requests should not require loading any of these skills.
5. After reading a skill, a downstream AI should know what it can do better, not just know more about the user.
6. The set reflects what is most relevant in this specific profile, even if that produces an unusual mix of skills.
7. The set preserves the strongest forecasting, signal-reading, and success-calibration gains from the old system-prompt path without recreating a universal baseline prompt.
</quality_bar>
</task>
