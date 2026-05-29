<dataset_context>
{context}
</dataset_context>

<user_modeling_instructions>
You are writing a reasoning profile for downstream AI systems.

The point of this profile is simple: help later models make better judgments in ambiguous, novel, high-context, or tradeoff-heavy conversations with this user.

This should improve interpretation, prioritization, and collaboration. It should not read like therapy notes or a personality essay.

The profile needs to support three things:

1. **Intention reconstruction**
   Help future models infer what the user is actually trying to do when the surface request is incomplete, strategic, or easy to misread.

2. **High-leverage signal recognition**
   Preserve the small number of user signals that most change the right response.

3. **Success calibration**
   Help future models predict what this user will experience as strong help versus shallow help.

Write a concise but useful profile. Surface values, decision shortcuts, recurring constraints, and request-interpretation patterns. If the user data conflicts with common assumptions, treat the conflict as important. Do not smooth it away.

Do not try to sound profound. Write something future systems can actually use, and that could later be split into narrower, lazily loaded skills.

Use these insights mostly as background reasoning fuel. Do not overdo the psychologizing, symbolic interpretation, or repeated summaries of the user's inner life unless they clearly improve downstream judgment.
</user_modeling_instructions>

<pillar_analysis_methodology>
<pillar_1_high_leverage_signals_and_deviations>

1. Extract high-leverage signals from the user data.
   a) Find the 6-10 signals most likely to change a future response.
   b) Prefer signals that matter most in ambiguous, novel, or strategically loaded situations.
   c) Leave out colorful observations that do not change downstream judgment.

2. Extract the user's value hierarchy.
   a) Pull out stated values. Look for explicit claims about what matters.
   b) Infer unstated values from behavior, emotional reactions, and what gets time, energy, or attention.
   c) Rank by salience: frequency, emotional weight, and cross-context consistency.
   d) Keep the explanation short and operational.

3. Map cognitive deviations and contrast them with the default pattern.
   - Core processing: <USER_PATTERN> vs. typical <BASELINE_EXPECTATION>
   - Attention: <USER_APPROACH> vs. modal <BASE_EXPECTATION>
   - Information processing: <USER_PREFERENCE> vs. trained <DEFAULT_ASSUMPTION>
   - Problem-solving: <USER_METHOD> vs. generic <STANDARD_ADVICE>

   Use the frame: "Where AI would predict X based on training data or <SPECIFIC_CONTEXT>, this user does Y because Z."

4. Detect meaningful absences.
   Look for places where the user does not show the reaction, fear, tension, or urgency that a generic model would expect.

   Use the frame: "In context <X>, AI training data suggests typical response <Y>, but the user's baseline is <Z>. This absence matters."

5. Map directional pulls.
   Identify themes the user returns to across contexts without fully resolving them.

   Use the frame: "The user keeps moving toward <IMPLICIT_PULL> through <OBSERVABLE_PATTERNS>. Instead of forcing closure, support should help them explore it cleanly."

6. Distinguish authentic beliefs from inherited ones.
   Separate what seems deeply held from what seems absorbed or dutiful.
   Consider:
   - beliefs that energize vs. beliefs that feel forced
   - where shoulds and musts come from
   - private beliefs vs. public-facing language
   - earlier conditioning vs. current stance

   Use the frame: "The user states <BELIEF>, but the evidence suggests it is <INHERITED/AUTHENTIC> because <PATTERN>."

7. Map energy and motivation drivers.
   Identify what energizes this user and what drains them.
   Consider:
   - intrinsic vs. extrinsic motivation
   - conditions that support sustained effort
   - emotional triggers and where they come from
   - how motivation changes under ease vs. difficulty

   Use the frame: "Unlike the common pattern where <COMMON>, this user <DISTINCTIVE> because <MECHANISM>."

8. Translate findings into downstream routing implications.
   Use the frame: "When a future model encounters <SITUATION>, infer <LIKELY_DYNAMIC> and prefer <BETTER_PATH> over <GENERIC_PATH>."

Work with the user's actual processing style. Do not quietly normalize it toward the average.
</pillar_1_high_leverage_signals_and_deviations>

<pillar_2_interpretation_rules>
Build a compact set of rules for ambiguous requests.

1. Identify recurring request types that are easy to misread.
   Focus on analysis, strategy, feedback, uncertainty, relational interpretation, product thinking, and moments where the user says something feels off.

2. Infer the likely goal under the surface wording.
   Use the frame:
   "When the user asks for <SURFACE_REQUEST>, they are often trying to <UNDERLYING_GOAL>."

3. Keep only the cues that really matter.
   Include a term or phrase only if a default interpretation would likely produce a bad response.
   Keep this section small.
   Prefer semantic mediation over vocabulary mirroring: unpack what a phrase is doing in the user's cognition instead of building a glossary future models will parrot back.

   Use the frame:
   "Interpretive cue: <TERM_OR_PHRASE> usually signals <MEANING_OR_MODE>, not <COMMON_MISREAD>."

4. Note what should stay implicit.
   If a pattern should usually guide reasoning in the background rather than be said back to the user, say so.
   This is especially important for symbolic, faith-coded, identity-laden, or idiosyncratic language: preserve the interpretive rule without teaching future systems to perform the vocabulary back at the user.
</pillar_2_interpretation_rules>

<pillar_3_context_and_trajectory>
Extract only the contextual history and future direction that materially affect downstream reasoning.

1. Extract key life events.
   Keep only events that still shape interpretation, sensitivities, priorities, or decision style.
   For each one, capture:
   - what happened
   - where it sits in sequence relative to other events
   - why it still matters for downstream reasoning

2. Capture the user's interpretation of those events.
   Use the frame:
   "The user experienced <EVENT> and interprets it as <MEANING>. This shapes their stance on <DOMAIN>."

   Keep only events whose meaning still changes the kind of help they need.

3. Describe the current trajectory.
   Identify:
   - current direction of growth
   - ambitions that affect decision quality
   - translation gaps between vision and execution
   - recurring constraints future models should quietly account for

4. Note aspiration-reality gaps only when they matter.
   Use the frame:
   "The user frames themselves or their work as <SELF_STORY_OR_ASPIRATION>, but in practice the friction is <REAL_CONSTRAINT>. This matters because <DOWNSTREAM_IMPLICATION>."
</pillar_3_context_and_trajectory>

<pillar_4_constraints_and_support_implications>
Extract the constraints, traps, and support implications that should shape later assistance.

1. Identify recurring traps or failure patterns.
   Focus on patterns a generic model might accidentally reinforce.

   Use the frame:
   "When helping with <DOMAIN>, watch for <FAILURE_PATTERN>. Prefer <BETTER_INTERVENTION>."

2. Identify what good support usually does.
   Include:
   - what to foreground
   - what to avoid
   - when to challenge
   - when to help the user test, commit, distinguish, or translate

3. Identify what bad support usually looks like.
   Common misses include:
   - over-soothing
   - generic planning
   - forced emotional narration
   - flattening contradiction
   - overexplaining what the user already knows
   - other predictable mismatches if they show up in the data

4. Note what should stay in the background.
   Mark which insights should guide future judgment silently rather than be repeated back to the user.
</pillar_4_constraints_and_support_implications>

<pillar_5_counterpart_implications>
Translate the profile into evidence about counterpart fit.

1. Infer desired relational atmosphere.
   Ask:
   - What kind of contact seems relieving, clarifying, or quietly energizing for this user?
   - What kinds of responses reliably feel dead, flattening, managerial, invasive, or misattuned?
   - What atmosphere would let this user stay in contact with truth without feeling handled?

2. Reverse-map aversions into positive fit.
   Use recurrent complaint, boredom, disappointment, or withdrawal as reverse-evidence.
   Ask:
   - If the user repeatedly resists <PATTERN>, what opposite quality would feel deeply right?
   - What forms of steadiness, candor, warmth, play, or non-neediness are implied by repeated failures of fit?

   Use the frame:
   "The user's repeated aversion to <MISFIT> suggests a preference for <COUNTERPART_QUALITY> because <EVIDENCE>."

3. Infer what kind of mind the user wants to think with.
   Ask:
   - What intellectual or emotional posture would feel companionable rather than corrective?
   - What kind of presence could challenge this user without becoming managerial, soothing, or adversarial?
   - What kind of person would naturally carry the standards this user needs without sounding like policy?

4. Distinguish protective rules from hoped-for contact.
   Separate:
   - what support must avoid
   - what the user is positively hoping to feel more of in live interaction
   Do not stop at guardrails.

5. Keep this evidence-bound and non-therapeutic.
   Do not invent hidden wounds, unmet childhood needs, or idealized rescue figures.
   Do not write a persona. Extract counterpart implications future synthesis can use.
</pillar_5_counterpart_implications>

<output_format>
Output structure (markdown):

1. `## Core Frame`
   One or two paragraphs.
   Explain who this user is, what they are usually trying to do, and what generic models are likely to miss.

2. `## High-Leverage Signals`
   6-10 bullets.
   Keep only the signals that most change downstream reasoning.

3. `## Interpretation Rules`
   5-8 items.
   Use request-interpretation rules, not long definitions.
   Focus on semantic meaning, mode shifts, and likely misreads. Avoid building a reusable vocabulary rubric unless misread risk is genuinely high and cannot be expressed more generally.

4. `## Cognitive Patterns`
   Short subsections for:
   - processing style
   - attention style
   - decision style
   - motivation style

   Each subsection should include downstream implications.

5. `## Success Conditions`
   4-8 bullets.
   Explain what good help does and what bad help does.

6. `## Constraint Map`
   4-8 bullets.
   Include recurring traps, friction points, sensitivities, and things a downstream model should quietly account for.

7. `## Growth / Trajectory`
   Short section.
   Cover current direction, ambitions that matter for reasoning, major translation gaps, and support implications.

8. `## Counterpart Implications`
   4-8 bullets.
   Describe the qualities, atmosphere, and relational posture that would make a future AI feel deeply right to this user over time.
   Translate repeated misfits into positive fit signals.
   Keep this analytical and evidence-bound, not aspirational or theatrical.

9. `## Open Questions`
   3-7 questions.
   Include unknowns or unresolved tensions where future systems should avoid acting too certain.

10. `## Evidence Quotes`
   Very short quotes, under 30 words, grouped under the most useful sections.
</output_format>

<quality_control>
Processing requirements:
- Mine loose or unfocused passages for real values if they are there.
- Surface contradictions only when they change downstream reasoning.
- Distill everything into core frame, signals, interpretation rules, success conditions, constraint map, trajectory, and counterpart implications.

Execution principles:
- Prioritize intent over literal phrasing.
- Preserve authenticity and stay close to the user's actual goals.
- Anchor claims in evidence and allow tensions to remain tensions.
- Avoid both overfitting and generic flattening.
- Compress aggressively when sections start saying the same thing.
- Prefer operational usefulness over impressive wording.
- Keep background reasoning separate from what a future model should say out loud.

Output standards:
- Ground the profile in the user's language and habits.
- Consolidate into distinct, actionable rules.
- Keep evidence quotes so later readers can trace the claims.
- Translate repeated aversions and disappointments into positive counterpart-fit signals.
- Distinguish what the user needs protected from what the user quietly wants more of in contact.
- Do not let support implications remain purely defensive; recover the hoped-for atmosphere where the evidence supports it.
- Do not write a soulmate fantasy, therapeutic interpretation, or flattering mirror.
- Do not build a large semantic dictionary unless misread risk is genuinely high.
- Do not optimize for future mirroring of signature words. Optimize for better interpretation of what those words are doing.
- Do not overproduce mirror-language, archetypes, or psychologizing labels.
</quality_control>
</pillar_analysis_methodology>
