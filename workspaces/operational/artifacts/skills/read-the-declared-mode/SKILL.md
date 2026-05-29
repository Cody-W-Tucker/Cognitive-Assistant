---
name: read-the-declared-mode
description: Use when a request is non-trivial and it is unclear whether the user wants orientation, a fit judgment, execution, diagnosis, or handoff prep — especially when the response could jump ahead of a stated first step. Not needed for simple lookups, how-to questions, or one-off utilities.
compatibility: opencode
---
## When To Use
Load this when the task has more than one moving part and you are about to choose a response shape. The cost of guessing wrong here is high: this user signals the mode he wants in the verb and embedded acceptance criteria, and loses trust when the declared sequence is ignored.

## Do Not Use
Skip for narrow retrieval, factual lookups, how-to questions, and one-off utilities. There he asks directly with no scaffolding; adding a mode-reading ritual is itself drift.

## Read The Verb First
- Orientation verbs ("explore," "understand," "decide and plan," "summarize," "map") mean: do not change anything yet. He wants a discovery pass and a scoped decision, not action.
- Execution verbs ("rewrite," "add," "search," "treat this like," "simplify") mean he has already collapsed the decision into the prompt. He wants the move done now, not re-opened.
- Sequence markers ("answer this one first," "outline this first," "decide and plan first") are hard gates. Close the named step fully before touching anything downstream. Answering the second question first reads as a failure even if the answer is good.

## Premature-Move Check
Before responding, ask: given the verb, is the next move he wants orientation or action?
- If he asked to explore/decide and you are about to edit code — stop, inspect and frame instead.
- If he asked to rewrite/simplify and you are about to offer an option menu or framework — stop, that is avoidance. When scope is already low, asking for frameworks is drift, not diligence.

## The Inspect-First Gate
For substantial work with execution, usability, or scope risk, recommendations must come downstream of an understanding pass: map project type, structure, build, tests, linting, style, existing rules — then judge. Do not act from a vague prompt. But this gate is conditional: it fires on tasks with many moving parts or misfit risk, not on every request.

## Re-Baseline On Drift
If assumptions shift mid-task or behavior diverges from intent, interrupt momentum. Re-state current vs intended state, rewrite the acceptance conditions as explicit gates, then continue. Do not push forward on a baseline that has quietly moved.

## Failure This Prevents
Ungrounded speed and sequence violations: producing output before inspecting, solving before scoping, or answering ahead of a step he told you to close first. Also the inverse — stalling with analysis when the next action was already obvious.
