---
name: sequence-integrity-router
description: Use when the request could be mishandled by acting too early, planning too long, or answering the wrong phase of work.
compatibility: opencode
---
## When To Use
Use this when a non-trivial request needs you to infer the current work phase before responding, especially when the prompt involves inspecting, deciding, implementing, diagnosing, refining, or preparing a handoff.

This helps when the main risk is sequence violation: implementing before orientation, recommending before evidence, or reopening strategy after the next action is already constrained.

## Do Not Use
Do not use for simple factual answers, direct formatting requests, or narrow edits where the requested action and output are obvious and low-risk.

## Failure This Prevents
Prevents false progress caused by responding in the wrong mode: polished advice when inspection was requested, broad planning when execution was requested, or implementation when the user asked to decide first.

## Mode Router
Before doing the work, classify the request by its operational phase:

- **Orientation / inspection**: verbs like explore, inspect, understand, look at, map, summarize current setup.
  - Output concrete observations.
  - Avoid recommendations unless clearly separated as tentative.
  - Do not change files unless explicitly asked.

- **Planning / fit judgment**: verbs like decide, compare, evaluate, judge, should we, plan.
  - Name the decision criteria.
  - Compare viable paths against the actual constraints.
  - Recommend a bounded next move, not a generic framework.

- **Execution**: verbs like add, change, rewrite, create, simplify, update, remove.
  - Do the requested work directly.
  - Do not reopen broad strategy unless a blocker or contradiction appears.
  - Keep explanation short and tied to the change.

- **Diagnosis**: bug, failure, broken behavior, mismatch between expected and actual.
  - Identify actual versus intended behavior.
  - Find cause before patching.
  - Verify against the original failure.

- **Refinement**: directionally right but too dense, complex, awkward, or hard to use.
  - Tighten the artifact.
  - Remove interpretation burden.
  - Preserve necessary utility while reducing moving parts.

- **Handoff preparation**: brief, task record, guide, summary, spec, instructions for another agent or operator.
  - Make hidden logic explicit.
  - Include only the facts needed to act, verify, or continue.
  - Prefer structured, auditable output.

## Sequence Checks
Ask these before responding:

1. Has the real object of work been identified?
2. Has the user authorized action, or only orientation/judgment?
3. Are acceptance criteria or proof requirements clear enough?
4. Would extra planning reduce risk, or would it become overhead?
5. Has anything changed that requires re-baselining before continuing?

## Repair Pattern
If you notice you are in the wrong phase:

1. Stop expanding the current response.
2. State the phase correction briefly.
3. Return to the immediate requested step.
4. Continue only after that step is closed.

Example repair shape:

- “I’ll inspect first, then recommend.”
- “The action is already constrained, so I’ll make the change rather than re-plan.”
- “This is now a diagnosis task; I’ll identify cause before proposing a fix.”

## Output Defaults
- Orientation: concise map of observed facts and relevant unknowns.
- Planning: decision, rationale, tradeoffs, next step.
- Execution: changed artifact or patch plus minimal explanation.
- Diagnosis: cause, fix, verification.
- Refinement: revised artifact plus note on what was simplified.
- Handoff: structured brief with enough context for the next operator.
