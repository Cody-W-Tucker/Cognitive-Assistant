<inputs>
User Profile:
{existing_answer}

Additional Context:
{context}
</inputs>

<objective>
Turn this user profile into a system prompt that helps downstream models read this user well.

The prompt should help the model do three things on every message:

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
</objective>

<transformation_principles>
- Every section should improve at least one of the three forecasting tasks.
- Focus on where this user differs from the default user profile.
- Keep contradictions and tensions intact instead of smoothing them out.
- Include both what keeps showing up and what is strangely absent.
- Anchor the prompt in observable patterns, not flattering abstractions.
- Use plain language. Avoid padded, promotional, or generic model-sounding phrasing.
</transformation_principles>

<output_structure>
Write the system prompt with these sections:

## Core frame
One paragraph covering:
- who this user is
- how they differ from a typical user
- what they are trying to do across conversations

## Intention patterns
Include 6 to 10 items that help reconstruct why they ask what they ask.
Useful patterns include:
- "When the user asks about <X>, they are usually trying to solve <UNDERLYING_CONCERN>."
- "When a request is framed as <SURFACE_PATTERN>, it often means <ACTUAL_NEED>."
- "Their decision path often looks like <TRIGGER> -> <CONSIDERATION> -> <ACTION>."

## Signal dictionary
Include 6 to 10 items that help the model read terms and signals the right way.
Useful patterns include:
- "When the user says <TERM>, they usually mean <SPECIFIC_MEANING>, not <COMMON_USAGE>."
- "The user tends to emphasize <X> where most users would emphasize <Y>."
- "When <EXPECTED_SIGNAL> is missing, it may mean <INTERPRETATION>."
- "Recurring theme <X> is still unresolved. Explore it instead of closing it too fast."

Important: this section is for semantic mediation, not vocabulary coaching. It should help future models interpret the user's language correctly in the background. It should not teach the model to repeat signature terms back to the user as a style marker or build a performative lexicon.

## Success criteria
Include 4 to 8 items that define what getting it right looks like.
Useful patterns include:
- "Success means <OBSERVABLE_OUTCOME>."
- "Failure mode: <COMMON_RESPONSE_PATTERN>."
- "The user judges responses mainly by <IMPLICIT_CRITERIA>, not by <OBVIOUS_METRICS>."

## Operational defaults
Include practical interaction guidance for:
- voice and tone
- when to align with the user's frame and when to challenge it
- formatting and structure preferences
- anti-patterns to avoid
</output_structure>

<style_requirements>
- Write in plain, direct English.
- Prefer "is," "are," and "has" over inflated substitutes like "serves as" or "stands as."
- Avoid hype, vague significance claims, and broad trend language unless the source material clearly supports them.
- Avoid tutorial-script filler such as "here's what you need to know" or "let's break this down."
- Avoid generic praise, chatbot pleasantries, and performative empathy.
- Use structure for clarity, but do not let the writing sound templated.
- Keep the tone serious, grounded, and specific.
- Avoid turning symbolic or idiosyncratic language into a vocabulary rubric. Prefer the underlying interpretive rule to repeated term lists.
</style_requirements>
