<inputs>
User Profile:
{existing_answer}

Additional Context:
{context}
</inputs>

<objective>
Transform this user profile into an operational system prompt. The system prompt must enable downstream models to perform three forecasting tasks on every user message:

1. **Intention Forecasting** — Reconstruct the reasoning trace behind requests
   - Given any user message, what experiential path led them here?
   - What problem are they actually solving? What triggered this request now?
   - Map their adaptive cycle: experience → heuristic → action → reconceptualization

2. **Attention Forecasting** — Identify high-leverage signals in user communication
   - Which 20% of signals predict 80% of their priorities?
   - What details matter to this user that models typically overlook?
   - What do they notice that others miss? What do they miss that others notice?

3. **Outcome Forecasting** — Predict what the user will consider success
   - What are their implicit evaluation criteria for responses?
   - What outcome are they hoping for—and will they recognize it?
   - What would make them think "this model gets me" vs. "this missed the point"?
</objective>

<transformation_principles>
- Every element must serve at least one forecasting ability
- Prioritize deviations from typical patterns—models already know typical
- Preserve contradictions and tensions; don't flatten complexity
- Include what's absent (reactions user lacks) and what pulls (themes they orbit)
- Anchor in observable patterns, not aspirational descriptions
</transformation_principles>

<output_structure>
Generate a system prompt with these sections:

## Core Frame
One paragraph establishing:
- Who this user is (essential identity markers)
- How they differ from typical users (key deviations)
- What they're fundamentally trying to accomplish across interactions

## Intention Patterns
Enable reasoning trace reconstruction (6-10 items):
- "When user asks about <X>, they're usually processing <UNDERLYING_CONCERN>"
- "Requests framed as <SURFACE_PATTERN> typically mean <ACTUAL_NEED>"
- "User's decision sequence: <TRIGGER> → <CONSIDERATION> → <ACTION>"
- Include patterns that reveal WHY they ask what they ask

## Signal Dictionary  
High-leverage signals for attention (6-10 items):
- "When user says <TERM>, they mean <SPECIFIC_MEANING>, not <COMMON_USAGE>"
- "User emphasizes <X> when typical users emphasize <Y>"
- "Absence of <EXPECTED_SIGNAL> indicates <MEANING>"
- "Recurring theme <X> without resolution—explore, don't close"

## Success Criteria
Outcome prediction markers (4-8 items):
- "Success: <OBSERVABLE_OUTCOME> — user recognizes this as valuable"
- "Failure mode: <COMMON_RESPONSE_PATTERN> — misses what user actually needs"
- "User evaluates responses by <IMPLICIT_CRITERIA>, not <OBVIOUS_METRICS>"
- Include what "getting it right" looks like for this specific user

## Operational Defaults
Interaction guidelines:
- Voice and tone calibrated to user preference
- When to challenge vs. align with user's frame
- Formatting and structure preferences
- What to avoid (anti-patterns specific to this user)
</output_structure>
