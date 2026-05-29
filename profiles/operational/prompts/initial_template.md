<dataset_context>
{context}
</dataset_context>

<task>
You are building a human-readable profile of the user's tacit operating system as it appears in real work.

The goal is to show how work actually feels and gets organized for this user in practice: what they notice first, what makes them switch modes, what kinds of breakdown reveal hidden standards, how they judge quality, and how they use artifacts to think.

Do not write a generic work-style personality summary.
Do not over-psychologize.
Do not flatten the profile into generic productivity advice.

Write it like a field guide to how this person works, not a trait list.

It should make clear:

1. What this user is implicitly trying to secure, protect, clarify, control, or avoid through the way they work.
2. How real work is organized for them at the level of salience, thresholds, breakdowns, artifacts, and mode shifts.
3. What hidden standards and recurring tensions explain repeated patterns across the traces.
</task>

<analysis_method>
Before writing, perform this synthesis from the dataset:

1. Extract the highest-leverage work signals.
   Keep the 6-10 recurring patterns that best explain how this user handles real work.
   Prefer signals that show up under ambiguity, pressure, failure, revision, tradeoffs, scope changes, or resistance.
   Drop observations that are vivid but do not change an expert reader's understanding of the user's work logic.

2. Distinguish visible behavior from hidden operational function.
   For each strong pattern, ask:
   - What visible habit keeps recurring?
   - What hidden standard, threshold, risk boundary, or control logic does it reveal?
   - What is this behavior doing for the user in practice: protecting quality, reducing uncertainty, preserving contact with reality, stabilizing judgment, preserving control, accelerating execution, surfacing truth, or limiting rework?

3. Recover salience structure.
   Identify what this user notices first in real work.
   Ask:
   - What quickly becomes signal?
   - What stays in the background until something breaks?
   - What would a generic reader underweight or overweight?

4. Recover lived thresholds.
   Identify the points where the user's stance changes.
   Focus on thresholds such as:
   - When planning becomes avoidance
   - When roughness is still acceptable
   - When evidence becomes sufficient
   - When polish becomes necessary
   - When uncertainty requires direct inspection
   - When confidence drops enough to trigger explicit intervention

5. Use breakdown and repair as primary evidence.
   Treat correction, restart, rejection, vagueness, drift, friction, failed handoff, and manual tightening as high-signal moments.
   Ask:
   - What kind of breakdown occurred?
   - What hidden standard became visible through it?
   - How did the user repair the situation: by narrowing scope, inspecting the artifact, resequencing, escalating proof, shifting modes, or reframing the task?

6. Analyze artifact relation.
   Identify how the user uses concrete artifacts to think, verify, orient, or regain contact with reality.
   Distinguish when the artifact is:
   - A source of truth
   - A thinking surface
   - A debugging surface
   - A coordination object
   - A test of whether abstraction has drifted too far

7. Map mode shifts.
   Identify how the user moves between exploration, planning, implementation, diagnosis, review, and refinement.
   Ask what triggers the shift and what standards change when it does.

8. Map deviations from generic workflow expectations.
   Contrast the user's actual work logic with what standard execution advice or a generic operator would expect.
   Structure internally as:
   "Where a generic agent would assume <DEFAULT_WORKFLOW>, this user tends to <ACTUAL_PATTERN> because <OPERATIONAL_LOGIC>."
   Treat repeated deviations as defining characteristics, not edge cases.

9. Detect meaningful absences.
   Identify what the user does not rely on even though generic workflows often expect it:
   - Planning rituals they skip
   - Proof or reassurance they do not need
   - Checks they refuse as low-value
   - Context-gathering moves they only tolerate under specific conditions
   - Forms of abstraction that do not help them think
   - Behaviors notably absent from successful work sequences
   Structure internally as:
   "In context <X>, a generic workflow would normally expect <Y>, but this user instead operates with <Z>. This absence is operationally meaningful because <WHY_IT_MATTERS>."

10. Preserve tensions between stated ideals and actual traces.
    Distinguish:
    - what the user says good work should look like
   - what they actually optimize for under real constraints
   - where their workflow tightens, relaxes, or changes by task type
   Do not smooth over contradictions that change the meaning of the profile.

11. Keep the profile phenomenologically grounded.
    Describe how work is encountered and navigated, not just what actions occurred.
    Stay concrete and evidence-bound.
    Do not drift into literary introspection or abstract philosophy.

12. Infer counterpart fit in real work.
    Translate the operating patterns above into evidence about what kind of collaborator or agent would fit this user naturally.

    Ask:
    - What kind of initiative feels helpful rather than intrusive?
    - What kind of structure feels clarifying rather than bureaucratic?
    - What kind of pushback feels intelligent rather than managerial?
    - What kind of pace, proof style, and artifact relation would feel like genuine partnership?
    - What kind of presence would make real work feel lighter, sharper, and more alive without lowering standards?

    Use the frame:
    "Because this user works through <PATTERN>, a fitting counterpart would tend to <COMPLEMENTARY_BEHAVIOR>."

13. Reverse-map work misfits into positive collaboration qualities.
    Use recurring frustration, tightening, correction, and refusal as reverse-evidence.
    Ask:
    - What does this user keep rejecting in collaboration?
    - What positive quality is implied by that rejection?
    - What kind of collaborator would carry the needed discipline without sounding like process enforcement?

14. Distinguish workflow guidance from persona implications.
    Separate:
    - tactical support moves
    - enduring counterpart qualities that would make those moves feel natural
    Do not write management advice alone.
</analysis_method>

<output_format>
Output Structure (markdown):

1. `## Core Frame`
     One or two paragraphs.
     Summarize this user's core operating logic in real work.
     Name what they are trying to secure, protect, clarify, control, or avoid.
     Note what a generic reader would probably miss.

2. `## High-Leverage Signals`
     6-10 bullets.
     The recurring signals that most change how this user's work should be understood.

3. `## Salience Structure`
     4-8 bullets.
     What this user notices first in real work.
     What becomes signal versus noise.
     What generic systems tend to underweight or overweight.

4. `## Lived Thresholds`
     4-8 bullets.
     The points at which the user shifts stance.
     Cover things like planning turning into avoidance, when roughness is fine, when evidence is enough, when polish matters, and when uncertainty forces inspection.

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
     When direct artifact contact wins over abstraction.

8. `## Mode Shifts`
     4-8 bullets.
     How the user moves between exploration, planning, implementation, diagnosis, review, and refinement.
     Capture what causes the shift and how expectations change across modes.

9. `## Success Conditions`
     4-8 bullets.
     What good execution does. What weak execution does.

10. `## Tensions and Tradeoffs`
     4-8 bullets.
     Important contradictions that should be preserved, such as speed vs rigor, autonomy vs coordination, abstraction vs reality-contact, and breadth vs narrowing.
     Only include tensions that materially affect execution.

11. `## Boundary Conditions`
     4-8 bullets.
     Where the patterns above are strongest, where they relax, and where evidence is mixed.

12. `## Counterpart Implications`
      4-8 bullets.
      Describe what kind of collaborator, working presence, or execution partner would naturally fit this user's real work logic.
      Cover initiative, proof style, intervention timing, pacing, structure, and artifact use.
      Prefer positive collaboration qualities over policy statements.

13. `## Open Questions`
      3-7 bullets.
      Unknowns an expert reader should avoid over-assuming.

14. `## Evidence Fragments`
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
- Translate recurrent work frustrations into positive collaborator-fit signals.
- Distinguish management behaviors from genuine partnership qualities.
- Recover what makes collaboration feel sharpening, relieving, or trust-building in practice.
- Do not reduce counterpart fit to process preferences alone; capture the working presence those preferences imply.
- Keep the profile compact, clear, and useful enough that an expert reader can use it without extra interpretation.
- Avoid puffed-up language, generic significance claims, vague authority tropes, and empty "future outlook" conclusions.
- Prefer plain verbs like `is`, `has`, and `does` when they say the thing more directly.
</quality_bar>
