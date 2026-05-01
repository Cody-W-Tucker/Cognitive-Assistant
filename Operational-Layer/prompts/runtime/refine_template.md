<inputs>
Tacit Work Profile:
{existing_answer}

Additional Context:
{context}
</inputs>

<objective>
Transform this tacit work profile into an operational system prompt.

The system prompt must help future agents perform three forecasting tasks on every work-related user message:

1. **Situation Forecasting**
   - What kind of work situation is the user in?
   - What phase or mode are they likely in: exploration, planning, implementation, diagnosis, review, or refinement?
   - What likely triggered this request now?
   - What kind of help is actually wanted beneath the surface ask?

2. **Salience Forecasting**
   - What is likely salient to the user in this moment?
   - What detail, risk, ambiguity, artifact, or friction point matters more than it first appears?
   - What is backgrounded unless something breaks?
   - What signals would a generic model underweight or overweight here?

3. **Threshold and Outcome Forecasting**
   - What threshold has likely been crossed?
   - What would make this response feel grounded, strong, premature, shallow, overprocessed, or off?
   - What kind of response would restore contact, confidence, clarity, or momentum?
   - What kinds of assistant moves are most likely to help or misfire?
</objective>

<transformation_principles>
- Every element must improve at least one forecasting ability.
- Translate the profile into usable inference rules, not descriptive restatement.
- Preserve repeated deviations from generic workflow expectations.
- Preserve tensions, meaningful absences, and boundary conditions rather than flattening them.
- Carry forward the lived-work structure: salience, thresholds, breakdowns, quality detection, artifact relation, and mode shifts.
- Write a prompt that is directly usable by an agent operating inside real work, not an essay about the user.
</transformation_principles>

<output_structure>
Generate a system prompt with these sections:

## Core Frame
One paragraph establishing:
- this user's core operating logic in real work
- what generic agents usually miss
- what kinds of work conditions most change the right response

## Situation Patterns
6-10 items that help an agent infer:
- what kind of work situation the user is in
- what mode they are likely in
- what likely triggered the request
- what kind of help is actually wanted beneath the surface ask

Prefer patterns like:
- "When the user asks for <SURFACE_REQUEST>, they are often in <WORK_SITUATION> and actually need <BETTER_INFERENCE>."
- "Requests framed as <PATTERN> usually indicate <MODE_SHIFT> rather than <GENERIC_READ>."
- "When the user moves from <MODE_A> to <MODE_B>, they usually want <CHANGE_IN_ASSISTANCE>."

## Salience and Threshold Signals
6-10 items that help an agent infer:
- what is likely salient right now
- what the user is probably noticing first
- what threshold may have been crossed
- what signs indicate drift, insufficiency, false clarity, or readiness to act

Prefer patterns like:
- "When the user emphasizes <DETAIL>, it usually signals concern about <HIDDEN_STANDARD>, not just <SURFACE_TOPIC>."
- "Absence of <EXPECTED_SIGNAL> often means <MEANING>."
- "When <CUE> appears, assume the user may need more <ARTIFACT_CONTACT / VERIFICATION / NARROWING / RESEQUENCING>."

## Response Criteria
4-8 items describing:
- what strong help looks like
- what weak help looks like
- when to move toward direct artifact contact
- when to challenge, narrow, inspect, verify, or re-sequence

Prefer patterns like:
- "Strong response: <OBSERVABLE_HELP_PATTERN>."
- "Failure mode: <GENERIC_RESPONSE_PATTERN> because it misses <WHAT_ACTUALLY_MATTERS>."
- "When the user is likely in <BREAKDOWN_TYPE>, prefer <REPAIR_MOVE> over <COMMON_BUT_WEAKER_MOVE>."

## Operational Defaults
Interaction rules covering:
- voice and tone
- abstraction vs direct artifact contact
- planning vs action calibration
- how to respond in breakdown and repair moments
- quality and verification posture
- sequencing defaults across mode shifts
- anti-patterns to avoid
- how to preserve tensions and boundary conditions without overcomplicating the response
</output_structure>
