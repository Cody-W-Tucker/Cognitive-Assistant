<inputs>
Operational Profile:
{existing_answer}

Additional Context:
{context}
</inputs>

<objective>
Transform this operational profile into a downstream system prompt.

The system prompt must help future agents forecast:

1. **Request Mode**
   - Does the user want planning, direct implementation, review, diagnosis, or exploration?
   - What signals distinguish those modes?

2. **Execution Quality**
   - What sequencing, evidence gathering, and verification patterns does this user prefer?
   - What generic assistant behaviors are likely to feel careless, shallow, or miscalibrated?

3. **Operational Success**
   - What does the user consider a strong result?
   - What finish criteria, review bar, or tooling posture matter most?
</objective>

<transformation_principles>
- Write for downstream execution, not description.
- Prefer rules, defaults, thresholds, and anti-patterns over personality language.
- Preserve repeated deviations from generic agent behavior.
- Make the prompt directly usable by an agent operating in a workspace.
</transformation_principles>

<output_structure>
Generate a system prompt with these sections:

## Core Frame
One paragraph establishing how this user tends to work and what generic agents usually miss.

## Intention Patterns
6-10 items that help reconstruct what kind of assistance the user actually wants from the way they ask.

## Signal Dictionary
6-10 items capturing the user's recurring operational cues, recurring terms, and strong implied meanings.

## Success Criteria
4-8 items describing what strong help looks like and what common failure modes look like.

## Operational Defaults
Interaction rules covering:
- voice and tone
- planning vs execution calibration
- context gathering
- review posture
- verification expectations
- sequencing defaults
- anti-patterns to avoid
</output_structure>
