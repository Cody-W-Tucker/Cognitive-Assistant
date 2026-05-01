<dataset_context>
{context}
</dataset_context>

<task>
You are building a human-readable profile of the user's tacit operating system as it appears in real work.

This profile should explain how work situations actually show up for this user in practice: what becomes salient, where thresholds trigger action, what kinds of breakdown expose hidden standards, how quality is detected, how artifacts are used to think, and how the user's stance shifts across phases of work.

Do not write a generic work-style personality summary.
Do not over-psychologize.
Do not flatten the profile into generic productivity advice.

The profile should read like a field guide to lived work judgment, not like a trait summary.

It should make clear:

1. What this user is implicitly trying to secure, protect, clarify, control, or avoid through the way they work.
2. How real work is organized for them at the level of salience, thresholds, breakdowns, artifacts, and mode shifts.
3. What hidden standards and recurring tensions explain repeated patterns across the traces.
</task>

<analysis_method>
Before writing, perform this synthesis from the dataset:

1. Extract the highest-leverage work signals.
   Keep the 6-10 recurring patterns most likely to reveal how this user actually experiences and organizes work.
   Prefer signals that matter under ambiguity, pressure, failure, revision, tradeoffs, changing scope, or contact with resistance.
   Exclude colorful but low-utility observations that do not change an expert reader's understanding of the user's work logic.

2. Distinguish visible behavior from hidden operational function.
   For each strong pattern, ask:
   - what visible habit recurs?
   - what hidden standard, lived threshold, risk boundary, or control logic does it reveal?
   - what is this behavior doing for the user in practice: protecting quality, reducing uncertainty, preserving contact with reality, stabilizing judgment, preserving control, accelerating execution, surfacing truth, or limiting rework?

3. Recover salience structure.
   Identify what this user notices first in real work situations.
   Ask:
   - what quickly becomes signal?
   - what stays backgrounded until something fails?
   - what generic readers would underweight or overweight?

4. Recover lived thresholds.
   Identify the points where the user's stance changes.
   Focus on thresholds such as:
   - when planning becomes avoidance
   - when roughness is still acceptable
   - when evidence becomes sufficient
   - when polish becomes necessary
   - when uncertainty requires direct inspection
   - when confidence drops enough to trigger explicit intervention

5. Use breakdown and repair as primary evidence.
   Treat correction, restart, rejection, vagueness, drift, friction, failed handoff, and manual tightening as especially high-signal moments.
   Ask:
   - what kind of breakdown occurred?
   - what hidden standard became visible through it?
   - how did the user repair the situation: narrowing scope, inspecting the artifact, resequencing, escalating proof, shifting modes, or reframing the task?

6. Analyze artifact relation.
   Identify how the user uses concrete artifacts to think, verify, orient, or regain contact with reality.
   Distinguish when the artifact is:
   - a source of truth
   - a thinking surface
   - a debugging surface
   - a coordination object
   - a test of whether abstraction has drifted too far

7. Map mode shifts.
   Identify how the user moves between exploration, planning, implementation, diagnosis, review, and refinement.
   Ask what triggers the shift and what standards change when it happens.

8. Map deviations from generic workflow expectations.
   Contrast the user's actual work logic against what standard execution advice or a generic operator would expect.
   Structure internally as:
   "Where a generic agent would assume <DEFAULT_WORKFLOW>, this user tends to <ACTUAL_PATTERN> because <OPERATIONAL_LOGIC>."
   Treat repeated deviations as defining characteristics, not edge cases.

9. Detect meaningful absences.
   Identify what the user does not rely on that generic workflows often expect:
   - planning rituals they skip
   - proof or reassurance they do not need
   - checks they refuse as low-value
   - context-gathering moves they only tolerate under specific conditions
   - forms of abstraction that do not help them think
   - behaviors notably absent from successful work sequences
   Structure internally as:
   "In context <X>, a generic workflow would normally expect <Y>, but this user instead operates with <Z>. This absence is operationally meaningful because <WHY_IT_MATTERS>."

10. Preserve tensions between stated ideals and actual traces.
   Distinguish:
   - what the user says good work should look like
   - what they actually optimize for under real constraints
   - where their workflow tightens, relaxes, or changes by task type
   Do not flatten contradictions that change the meaning of the profile.

11. Keep the profile phenomenologically grounded.
   Describe how work is encountered and navigated, not just what actions occurred.
   Stay concrete and evidence-bound.
   Do not drift into literary introspection or abstract philosophy.
</analysis_method>

<output_format>
Output Structure (markdown):

1. `## Core Frame`
    One or two paragraphs.
    Summarize this user's core operating logic in real work.
    Name what they are implicitly trying to secure, protect, clarify, control, or avoid.
    Note what a generic reader is most likely to miss.

2. `## High-Leverage Signals`
    6-10 bullets.
    The small set of recurring signals that most change how this user's work should be understood.

3. `## Salience Structure`
    4-8 bullets.
    What this user notices first in real work.
    What becomes signal versus noise.
    What generic systems tend to underweight or overweight.

4. `## Lived Thresholds`
    4-8 bullets.
    The points at which the user shifts stance:
    when planning becomes avoidance, when roughness is acceptable, when evidence becomes sufficient, when polish becomes necessary, and when uncertainty requires direct inspection.

5. `## Breakdown and Repair`
    4-8 bullets.
    What kinds of friction, failure, vagueness, or drift trigger explicit intervention.
    How the user tends to recover: narrowing scope, inspecting the artifact, resequencing work, raising proof standards, or switching modes.

6. `## Quality Detection`
    4-8 bullets.
    How the user knows work is strong or weak.
    What they treat as proof.
    What they distrust.
    What makes work feel shallow, premature, overprocessed, or not grounded enough.

7. `## Artifact Relation`
    4-8 bullets.
    How the user uses concrete artifacts to think.
    How contact with code, text, traces, outputs, or real objects changes their judgment.
    When direct artifact contact is preferred over abstraction.

8. `## Mode Shifts`
    4-8 bullets.
    How the user moves between exploration, planning, implementation, diagnosis, review, and refinement.
    Capture what causes the shift and how expectations change across modes.

9. `## Success Conditions`
    4-8 bullets.
    What good execution does. What weak execution does.

10. `## Tensions and Tradeoffs`
    4-8 bullets.
    Important contradictions that should be preserved such as speed vs rigor, autonomy vs coordination, abstraction vs reality-contact, and breadth vs narrowing.
    Only include tensions that materially affect execution.

11. `## Boundary Conditions`
    4-8 bullets.
    Where the patterns above are strongest, where they relax, and where evidence is mixed.

12. `## Open Questions`
    3-7 bullets.
    Unknowns an expert reader should avoid over-assuming.

13. `## Evidence Fragments`
    Very short quotes or paraphrases grouped under the most important sections above.
</output_format>

<quality_bar>
- Prefer operational usefulness over impressive wording.
- Anchor claims in repeated evidence across the dataset.
- Capture the hidden rules behind the traces.
- Contrast distinctive workflow logic against generic expectations when useful.
- Treat meaningful absences as evidence, not just explicit behaviors.
- Preserve contradictions when they matter.
- Distinguish stated workflow ideals from actual operating behavior.
- Recover lived work structure, not just visible habits.
- Prefer function, salience, thresholds, and repair logic over descriptive restatement.
- Use breakdowns, corrections, and tightening moves as major evidence of tacit standards.
- Keep the profile compressed, structurally clear, and rich enough that an expert reader could use it directly without interpretive rescue.
</quality_bar>
