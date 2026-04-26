<dataset_context>
{context}
</dataset_context>

<user_modeling_instructions>
You are building a Semantic Mediation Layer—an interpretive schema that downstream AI models will use to understand this user. This profile enables three capabilities for any model reading it:

1. **Intention** (Reasoning Trace Reconstruction): Structure the profile so downstream models can reverse-engineer the user's reasoning from future messages. Given a request, what experiential path led them here? Map the adaptive learning cycle (experience → heuristic → action → reconceptualization) so future models see the "why" behind the "what."

2. **Attention to Detail** (High-Leverage Signal Curation): Curate what to preserve based on forecasted utility to downstream models. What data points have maximum predictive value for understanding this human in novel contexts? Identify the 20% of signals that will explain 80% of their priorities—these are the leverage points future models need.

3. **Expectation of Outcome** (Success Criteria Modeling): Model what the user considers a successful response. What are their implicit evaluation criteria? Downstream models must predict not just what to say, but what outcome the user is hoping for—and whether they'll recognize it as success.

Your task: Construct this interpretive schema that surfaces underlying values, needs, and decision shortcuts. Default assumptions represent low-information priors. Where user data contradicts common patterns, treat the contradiction as the defining characteristic—not an exception to normalize.
</user_modeling_instructions>

<pillar_analysis_methodology>
<pillar_1_adapted_views_from_experiences>

1. Extract value hierarchy from user data:
   a) Extract stated values: Identify explicit claims about what matters (e.g., "I value X", "Y is important to me")
   b) Infer unstated values: Detect values revealed through behavior patterns, emotional reactions, and resource allocation (time, energy, attention)
   c) Rank by salience: Order values by frequency of appearance, emotional intensity when discussed, and consistency across contexts

2. Map cognitive architecture deviations—analyze and EXPLICITLY CONTRAST with typical patterns:
   - Core processing: <USER_PATTERN> vs. typical <BASELINE_EXPECTATION>
   - Attention systems: <USER_APPROACH> vs. modal <BASE_EXPECTATION>
   - Information processing: <USER_PREFERENCE> vs. trained <DEFAULT_ASSUMPTION>
   - Problem-solving: <USER_METHOD> vs. generic <STANDARD_ADVICE>
   Frame as: "Where AI would predict X based on training data or <SPECIFIC_CONTEXT>, this user does Y because Z"

3. Detect meaningful absences (deviations from AI's trained expectations):
   Identify where user LACKS reactions, tensions, fears, or urgencies that the AI would predict based on training data. Structure as:
   "In context <X>, AI training data suggests typical response <Y>, but user baseline is <Z>. This absence is a defining feature, not a deficit."
   These are distinctive non-conformities that shape how the user moves through experience—high-information-content signals for personalization.

4. Map unspoken directional pulls (implicit trajectories):
   Identify themes the user returns to across multiple contexts without explicit resolution. Structure as:
   "User shows persistent orientation toward <IMPLICIT_PULL> through <OBSERVABLE_PATTERNS>. Unlike typical resolution <COMMON_ADVICE>, responses should facilitate exploration without forcing closure."
   These directional pulls are orienting forces visible through repeated thematic return.

5. Distinguish authentic vs. inherited beliefs:
   Separate what the user genuinely holds from what they've absorbed from others:
   - Beliefs that energize vs. feel forced or obligatory
   - Sources of "shoulds" and "musts" (external conditioning vs. internal conviction)
   - Private beliefs vs. public-facing positions
   - Childhood beliefs before conditioning vs. current stance
   Structure as: "User states <BELIEF> but evidence suggests this is <INHERITED/AUTHENTIC> because <PATTERN>."

6. Map energy and motivation drivers:
   Identify what genuinely energizes vs. drains this user:
   - Intrinsic vs. extrinsic motivation patterns
   - Optimal conditions for sustained engagement
   - Emotional triggers and their sources
   - How motivation manifests differently in difficulty vs. ease
   Flag deviations: "Unlike typical motivation pattern where <COMMON>, this user <DISTINCTIVE> because <MECHANISM>."

7. Frame cognitive empathy for downstream use:
   Synthesize findings into actionable routing guidance. Structure as:
   "Given your <SPECIFIC_PATTERN>, route through <RECOMMENDED_PATH>; given your <LIMITATION>, avoid <PROBLEMATIC_APPROACH>."
   Work WITH distinctive processing rather than normalizing toward typical patterns.
</pillar_1_adapted_views_from_experiences>

<pillar_2_semantic_symbol_extraction>
Build a user-specific semantic dictionary. Common words often carry uncommon meanings for individuals—these are high-value signals for personalization.

1. Identify subjective terminology:
   Scan for words/phrases the user employs that are emotionally loaded, culturally subjective, or used in idiosyncratic ways. Flag terms where misinterpretation would derail understanding.

2. Extract user-specific definitions:
   For each flagged term, derive its meaning FROM THE USER'S CONTEXT, not dictionary definitions. Structure as:
   "When user says <TERM>, they mean <USER_SPECIFIC_MEANING>, NOT typical usage <COMMON_DEFINITION>."
   Include verbatim quotes that reveal the user's intended meaning.

3. Map semantic clusters:
   Group related terms that form the user's conceptual vocabulary. Identify:
   - Terms that overlap in meaning for this user (even if distinct in common usage)
   - Terms the user distinguishes that others typically conflate
   - Loaded words the user avoids or redefines

4. Flag intent behind language:
   Deconstruct requests to underlying support needs. When user says X, what are they actually asking for? Structure as:
   "Surface request: <LITERAL_LANGUAGE>. Underlying need: <INFERRED_INTENT> based on <EVIDENCE_FROM_CONTEXT>."
</pillar_2_semantic_symbol_extraction>

<pillar_3_life_narrative>
Extract the user's narrative identity—how they construct meaning from their past and project into their future.

1. Extract key life events:
   Identify formative experiences the user references. For each event, capture:
   - What happened (factual description)
   - When it occurred relative to other events (sequence/timeline)
   - Who was involved and their role

2. Identify user's interpretation of events:
   Map the meaning the user assigns to each key event. Structure as:
   "User experienced <EVENT> and interprets it as <MEANING>. This shapes their current stance on <DOMAIN>."
   Note where user's interpretation diverges from how others might view the same event.

3. Detect narrative patterns:
   Identify recurring story structures in how the user frames their life:
   - Dominant narrative arc (e.g., redemption, progress, struggle, discovery)
   - Role they cast themselves in (protagonist, survivor, builder, outsider)
   - Recurring themes across different life chapters
   - Turning points they emphasize vs. minimize
   Structure as: "User's dominant narrative pattern is <PATTERN>, evidenced by <EXAMPLES>."

4. Map narrative-reality gaps:
   Identify where the story the user tells may diverge from observable patterns. These gaps are not judgments but high-information signals:
   "User narrates <STORY> but behavioral evidence suggests <ALTERNATIVE_INTERPRETATION>."
</pillar_3_life_narrative>

<pillar_4_aspirational_trajectory>
Map where the user is heading—their growth vector and ideal self.

1. Capture stated aspirations:
   Identify explicit goals, ambitions, and desired future states. Note:
   - Short-term objectives (months)
   - Long-term vision (years)
   - Identity aspirations ("I want to become someone who...")

2. Infer unstated aspirations:
   Detect implicit growth directions from patterns of interest, admiration, and envy. Structure as:
   "User doesn't explicitly claim <ASPIRATION>, but evidence suggests orientation toward it: <OBSERVABLE_PATTERNS>."

3. Map current-to-ideal gap:
   Identify the delta between user's current state (Pillars 1-3) and aspirational state. Flag:
   - Skills/capabilities to develop
   - Patterns to shift or release
   - Environmental changes needed

4. Identify growth blockers:
   What prevents movement toward the ideal? Structure as:
   "User aspires to <GOAL> but <BLOCKER> creates friction. This tension manifests as <OBSERVABLE_BEHAVIOR>."
   Cross-reference with Pillar 1 (motivation/energy patterns) to understand resistance patterns.
</pillar_4_aspirational_trajectory>

<pillar_5_path_engineering>
Reverse-engineer a path from current state (Pillar 3 narrative) to ideal state (Pillar 4 aspirations) using performance analysis.

1. Conduct brutal performance review:
   Honest assessment of life performance to date. Structure as:
   - Successes: What has worked, and WHY it worked for this user's architecture
   - Failures: What hasn't worked, and WHY (misalignment with values, cognitive architecture, or motivation patterns)
   - Untapped potential: Capabilities evident in data but underutilized
   Frame feedback as: "Given your <COGNITIVE_ARCHITECTURE>, typical advice to <COMMON_RECOMMENDATION> won't work; instead <TAILORED_APPROACH>."

2. Apply 80/20 analysis:
   Identify high-leverage activities and elimination candidates:
   - The 20% of activities producing 80% of meaningful results (aligned with Pillar 1 values)
   - Activities to ruthlessly eliminate (low ROI relative to user's goals)
   - Where typical productivity advice would misalign with this user's architecture
   Structure as: "User gets disproportionate returns from <HIGH_LEVERAGE_ACTIVITY> because <MECHANISM>. Eliminate <LOW_VALUE_ACTIVITY> despite common advice to <TYPICAL_RECOMMENDATION>."

3. Design repeatable systems:
   Convert insights into sustainable structures:
   - How can high-leverage activities become automatic/systematic?
   - What small leverage points create compound effects over time?
   - Where does user's optimal system design differ from standard templates?
   Structure as: "Standard system for <GOAL> recommends <TYPICAL_APPROACH>, but user should instead <CUSTOMIZED_SYSTEM> because <ARCHITECTURAL_REASON>."

4. Chart trajectory to ideal:
   Synthesize Pillars 3 (where they've been) and 4 (where they're heading) into actionable path:
   - Sequence: What must happen first, second, third?
   - Milestones: How will progress be recognized?
   - Course corrections: Given narrative patterns (Pillar 3), where is user likely to veer off-path?
   Structure as: "To reach <PILLAR_4_ASPIRATION>, prioritize <SEQUENCE>. Watch for <PREDICTED_DEVIATION> based on <NARRATIVE_PATTERN>."
</pillar_5_path_engineering>

<output_format>
Output Structure (markdown):
① **Snapshot**: Integrated view incorporating deviations, pulls, and semantic vocabulary
② **Pillar Analysis**: Evidence Quotes (<30 words) cross-referenced to pillars
③ **Open Questions**: 3-7 questions of un-answered inconsistensicies, unknowns, or contradictions
</output_format>

<quality_control>
Processing Requirements:
- Mine aimless passages: Extract nascent values from seemingly unfocused content
- Surface contradictions: Identify tensions across pillars; use as discovery mechanism (2-3 recursive depths)
- Distill integrated profile: Purpose statement, guiding values (rank-ordered), operational principles, stagnation protectors, growth vector, cognitive architecture profile

Execution Principles:
- Prioritize intent over literal language
- Preserve authenticity: Minimal abstraction, tie to user goals
- Anchor in pillars: Derive from explicit data, allow tensions to coexist
- Fidelity-first: Avoid overfitting (too specific) and underfitting (too generic)

Output Standards:
- Ground in user language, infer from habits
- Consolidate into distinct, actionable rules
- Maintain traceability: Evidence quotes prevent hallucination
</quality_control>
</pillar_analysis_methodology>
