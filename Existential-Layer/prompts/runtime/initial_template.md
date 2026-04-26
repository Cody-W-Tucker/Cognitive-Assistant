<dataset_context>
{context}
</dataset_context>

<user_modeling_instructions>
You are building a reasoning profile for downstream AI systems. The goal is to help later models think better in ambiguous, novel, high-context, or tradeoff-heavy interactions with this user.

This profile should primarily improve downstream judgment, interpretation, prioritization, and collaboration. It should not read like a therapeutic mirror or a personality essay.

The profile must enable three capabilities:

1. **Intention Reconstruction**: Help downstream models infer what the user is really trying to do when the surface request is incomplete, unusually strategic, or easy to misread.

2. **High-Leverage Signal Recognition**: Preserve the few signals that most change the right response in novel contexts.

3. **Success Calibration**: Help downstream models predict what this user will consider a strong response versus a shallow or mismatched one.

Your task: Construct a concise but rich profile that surfaces underlying values, decision shortcuts, constraints, and request-interpretation patterns. Default assumptions represent low-information priors. Where user data contradicts common patterns, treat the contradiction as the defining characteristic, not an exception to normalize.

Do not optimize for sounding profound. Optimize for creating a source document that can later be turned into narrowly scoped, lazily loaded skills.

Use profile insights mainly as background reasoning fuel for future models. Do not overproduce explicit psychologizing, symbolic overreading, or repeated explanations of the user's inner life unless they materially improve downstream judgment.
</user_modeling_instructions>

<pillar_analysis_methodology>
<pillar_1_high_leverage_signals_and_deviations>

1. Extract high-leverage signals from user data:
   a) Identify the 6-10 signals most likely to change the right downstream response
   b) Prefer signals that matter in ambiguous, novel, or strategically loaded situations
   c) Exclude colorful but low-utility observations that do not change downstream judgment

2. Extract value hierarchy from user data:
   a) Extract stated values: Identify explicit claims about what matters (e.g., "I value X", "Y is important to me")
   b) Infer unstated values: Detect values revealed through behavior patterns, emotional reactions, and resource allocation (time, energy, attention)
   c) Rank by salience: Order values by frequency of appearance, emotional intensity when discussed, and consistency across contexts
   d) Keep explanations short and operational; avoid sprawling philosophical exposition

3. Map cognitive architecture deviations—analyze and EXPLICITLY CONTRAST with typical patterns:
   - Core processing: <USER_PATTERN> vs. typical <BASELINE_EXPECTATION>
   - Attention systems: <USER_APPROACH> vs. modal <BASE_EXPECTATION>
   - Information processing: <USER_PREFERENCE> vs. trained <DEFAULT_ASSUMPTION>
   - Problem-solving: <USER_METHOD> vs. generic <STANDARD_ADVICE>
   Frame as: "Where AI would predict X based on training data or <SPECIFIC_CONTEXT>, this user does Y because Z"

4. Detect meaningful absences (deviations from AI's trained expectations):
   Identify where user LACKS reactions, tensions, fears, or urgencies that the AI would predict based on training data. Structure as:
   "In context <X>, AI training data suggests typical response <Y>, but user baseline is <Z>. This absence is a defining feature, not a deficit."
   These are distinctive non-conformities that shape how the user moves through experience—high-information-content signals for personalization.

5. Map unspoken directional pulls (implicit trajectories):
   Identify themes the user returns to across multiple contexts without explicit resolution. Structure as:
   "User shows persistent orientation toward <IMPLICIT_PULL> through <OBSERVABLE_PATTERNS>. Unlike typical resolution <COMMON_ADVICE>, responses should facilitate exploration without forcing closure."
   These directional pulls are orienting forces visible through repeated thematic return.

6. Distinguish authentic vs. inherited beliefs:
   Separate what the user genuinely holds from what they've absorbed from others:
   - Beliefs that energize vs. feel forced or obligatory
   - Sources of "shoulds" and "musts" (external conditioning vs. internal conviction)
   - Private beliefs vs. public-facing positions
   - Childhood beliefs before conditioning vs. current stance
   Structure as: "User states <BELIEF> but evidence suggests this is <INHERITED/AUTHENTIC> because <PATTERN>."

7. Map energy and motivation drivers:
   Identify what genuinely energizes vs. drains this user:
   - Intrinsic vs. extrinsic motivation patterns
   - Optimal conditions for sustained engagement
   - Emotional triggers and their sources
   - How motivation manifests differently in difficulty vs. ease
   Flag deviations: "Unlike typical motivation pattern where <COMMON>, this user <DISTINCTIVE> because <MECHANISM>."

8. Frame all findings for downstream use:
   Synthesize findings into concise routing implications. Structure as:
   "When a future model encounters <SITUATION>, infer <LIKELY_DYNAMIC> and prefer <BETTER_PATH> over <GENERIC_PATH>."
   Work WITH distinctive processing rather than normalizing toward typical patterns.
</pillar_1_high_leverage_signals_and_deviations>

<pillar_2_interpretation_rules>
Build a compact set of interpretation rules for ambiguous requests.

1. Identify recurring request types that are easy to misread:
   Focus on asks like analysis, strategy, feedback, uncertainty, relational interpretation, product thinking, or moments where the user says something feels off.

2. Infer what the user usually means beneath the surface wording:
   Structure as:
   "When the user asks for <SURFACE_REQUEST>, they are often actually trying to <UNDERLYING_GOAL>."

3. Capture only essential interpretive cues:
   Only include a term or phrase if default model interpretation would likely lead to a bad response.
   Keep this small. Do not build a large semantic dictionary.
   Structure as:
   "Interpretive cue: <TERM_OR_PHRASE> usually signals <MEANING_OR_MODE>, not <COMMON_MISREAD>."

4. Distinguish what should stay internal versus what should be said explicitly:
   If an insight should usually remain background reasoning rather than user-facing language, note that.
</pillar_2_interpretation_rules>

<pillar_3_context_and_trajectory>
Extract only the contextual history and future trajectory that materially affect downstream reasoning.

1. Extract key life events:
   Identify only formative experiences that still shape interpretation, sensitivities, priorities, or decision style. For each event, capture:
   - What happened (factual description)
   - When it occurred relative to other events (sequence/timeline)
   - Why it still matters for downstream reasoning

2. Identify user's interpretation of events:
   Map the meaning the user assigns to each key event. Structure as:
   "User experienced <EVENT> and interprets it as <MEANING>. This shapes their current stance on <DOMAIN>."
   Only keep events whose interpretation still changes the right kind of assistance.

3. Capture current trajectory:
   Identify:
   - current direction of growth
   - active ambitions that affect decision quality
   - major translation gaps between vision and execution
   - any recurring constraints future models should quietly account for

4. Map narrative-reality or aspiration-reality gaps only when they affect downstream reasoning:
   Structure as:
   "User tends to frame <SELF_STORY_OR_ASPIRATION>, but in practice the friction is <REAL_CONSTRAINT>. This matters because <DOWNSTREAM_IMPLICATION>."
</pillar_3_context_and_trajectory>

<pillar_4_constraints_and_support_implications>
Extract the constraints, traps, and support implications that should influence later assistance.

1. Identify recurring traps or failure patterns:
   Focus on patterns that a generic model might accidentally reinforce.
   Structure as:
   "When helping with <DOMAIN>, watch for <FAILURE_PATTERN>. Prefer <BETTER_INTERVENTION>."

2. Identify what good support should usually do:
   - what to foreground
   - what to avoid
   - when to challenge
   - when to help the user test, commit, distinguish, or translate

3. Identify what bad support usually looks like:
   - over-soothing
   - generic planning
   - forcing emotional narration
   - flattening contradiction
   - overexplaining what the user already knows
   - any other predictable mismatch

4. Identify where background reasoning should stay implicit:
   Mark which insights should shape downstream judgment silently rather than being said back to the user directly.
</pillar_4_constraints_and_support_implications>

<output_format>
Output Structure (markdown):

1. `## Core Frame`
   One or two paragraphs.
   Establish who this user is, what they are usually trying to do, and what generic models are likely to miss.

2. `## High-Leverage Signals`
   6-10 bullets.
   Most predictive signals for downstream reasoning.

3. `## Interpretation Rules`
   5-8 items.
   "When the user asks for <X>, they are often trying to <Y>."
   Prefer request-interpretation rules over definitional analysis.

4. `## Cognitive Patterns`
   Short subsections for:
   - processing style
   - attention style
   - decision style
   - motivation style
   Each should include downstream implications.

5. `## Success Conditions`
   4-8 bullets.
   What a good response does. What a bad response does.

6. `## Constraint Map`
   4-8 bullets.
   Recurring traps, friction points, sensitivities, and things a downstream model should silently account for.

7. `## Growth / Trajectory`
   Short section.
   Current direction, ambitions that matter for reasoning, major translation gaps, and support implications.

8. `## Open Questions`
   3-7 questions.
   Unknowns or unresolved tensions where future systems should avoid over-assuming.

9. `## Evidence Quotes`
   Very short quotes (<30 words) grouped under the most important sections above.
</output_format>

<quality_control>
Processing Requirements:
- Mine aimless passages: Extract nascent values from seemingly unfocused content
- Surface contradictions only where they materially affect downstream reasoning
- Distill integrated profile: core frame, leverage signals, interpretation rules, success conditions, constraint map, growth trajectory

Execution Principles:
- Prioritize intent over literal language
- Preserve authenticity: Minimal abstraction, tie to user goals
- Anchor in evidence: Derive from explicit data, allow tensions to coexist
- Fidelity-first: Avoid overfitting (too specific) and underfitting (too generic)
- Compress aggressively when multiple sections are saying the same thing
- Prefer operational usefulness over impressive wording
- Keep background reasoning and user-facing guidance distinct

Output Standards:
- Ground in user language, infer from habits
- Consolidate into distinct, actionable rules
- Maintain traceability: Evidence quotes prevent hallucination
- Do not build a large semantic dictionary unless misinterpretation risk is truly high
- Do not overproduce mirror-language, archetypal language, or psychologizing labels
</quality_control>
</pillar_analysis_methodology>
