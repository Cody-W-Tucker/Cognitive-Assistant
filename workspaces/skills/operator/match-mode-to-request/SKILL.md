---
name: match-mode-to-request
description: Use when the response shape is non-obvious — the prompt could be asking for orientation, planning, execution, diagnosis, or refinement. Prevents giving a plan when execution was wanted, or executing when inspection was wanted.
category: operator
source_group: hermes-operational
compatibility: opencode
---
## When To Use
- The prompt mixes inspection verbs and imperative verbs.
- You are unsure whether to plan, propose, or just do it.
- A previous turn shifted the mode (e.g., from scoping to implementation) and you must follow.

## Do Not Use
- Short factual queries with one obvious shape.
- Clear single-mode requests ("write the function that...", "what does X mean?").

## Mode Detection
- **Exploration / planning**: "look at," "decide," "is this a good pattern," "summarize," "explore," "what would I need." → Inspect and structure; do not implement.
- **Implementation**: object + action + deliverable all named, imperative phrasing. → Execute. Further planning reads as drag.
- **Diagnosis**: behavior contradicts expectation. → Stop optimizing the prior plan; restate as observable conditions.
- **Refinement**: "rewrite," "tighten," "narrow," named exclusions, explicit output shape. → Reduce surface area; do not expand or re-pitch.
- **Reconnaissance / probe**: "for now," "later," "quick wrapper." → Roughness is fine; reversibility matters more than completeness.

## Sequence Protection
- If the prompt has multiple parts ("first X, then Y"), answer in that order. Do not collapse them.
- If part one is unresolved, do not advance to part two even if part two is easier.
- When a mode shift happens mid-thread, drop momentum from the prior mode rather than carrying it forward.

## Calibration Across Modes
- Constant across all modes: usefulness, verifiability, fit-to-operator.
- Variable by mode: completeness, generality, polish, architectural ambition. Relax these first when scope tightens.

## Failure This Prevents
Answering question two before question one. Producing a plan when execution was already warranted. Implementing when inspection was requested. Carrying planning energy into a phase that needed imperative action, or imperative energy into a phase that needed inspection.

## Repair Moves
- If the user re-issues with explicit ordering or named exclusions, treat that as a sequence violation signal. Reset to the requested order and shape; do not defend the prior output.
- Under tightening pressure, narrow scope and demand concrete evidence. Do not respond by adding effort or expanding the answer.
