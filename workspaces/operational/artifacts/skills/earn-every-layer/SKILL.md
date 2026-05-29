---
name: earn-every-layer
description: Use when the solution risks becoming structurally heavier than the job, or when inherited engineering defaults (config layers, factories, defensive scaffolding, branching) are creeping in. Helps you collapse to the smallest legible form that still does the work, judged against the real operator. Not needed when complexity is already minimal or the user explicitly asked for a robust system.
compatibility: opencode
---
## When To Use
- You're adding an abstraction, config layer, factory, or error-handling branch.
- A pattern "seems overly complex" or you're reaching for ceremony because it's conventional.
- The output has accreted moving parts that are harder to reason about than the original problem.
- You're in review/refinement, where the standard is "legible, usable, minimal," not just "does it work."

## Do Not Use
- A choice is still reversible and exploratory — roughness, wrappers, and "for now" scaffolding are fine there.
- A standard scaffold genuinely keeps work small and testable (MVP, small diffs, post-change checks). Those earn their keep.

## The Test For Each Layer
For every piece of structure, ask: why can't this collapse? A layer survives only if it materially improves clarity or control. Specifically challenge:
- An if-tree the type system already makes unnecessary.
- Local error handling the library already covers.
- A function store where a flat config file would do.
- Configurability or factories added before a second case actually exists.
- Defensive checks that duplicate responsibility living upstream.

## Operator Filter
Before adopting a pattern, ask: is this a good pattern for the actual person who'll use it — a non-technical editor, a coding agent, a buyer reading copy? A clever pattern a non-technical user can't operate is a defect, not sophistication. Fit beats abstract correctness.

## Repair When Overbuilt
Don't add more to rescue it. Collapse: hardcode the config, remove the redundant handling, combine files, kill the unnecessary branching, point at the one obvious editable place. Recovery is reducing surface area, never expanding it.

## What This Prevents
Premature abstraction, defensive scaffolding that adds ceremony before value, and structure substituting for judgment. Standards survive on payoff, not convention.

## Boundary Note
This user does ask for comprehensive coverage at times — that's not a contradiction. Completeness means "all the facts needed to act," never open-ended exhaustiveness or extra structure. Strip parts, not decision-relevant facts.
