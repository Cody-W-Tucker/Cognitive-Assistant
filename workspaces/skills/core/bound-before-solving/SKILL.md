---
name: bound-before-solving
description: Use when a task carries design, implementation, or judgment weight and the real object hasn't been inspected yet. Helps when you're tempted to recommend, implement, or answer before touching the actual artifact. Not needed for simple factual lookups, quick troubleshooting, or one-off how-to questions.
category: core
source_group: hermes-operational
compatibility: opencode
---
## When To Use
Load this when the request involves a codebase, schema, config, prompt, copy, lead, or runtime behavior and the consequence of being wrong is real. The opening move is not to solve but to bound: name the object, surface the governing constraints and use context, name the operator who has to live with the result, then narrow until the next move is obvious.

## Do Not Use
Skip for simple factual questions, quick how-to, or troubleshooting where the answer is direct and reversible. Forcing an orientation pass onto a trivial ask creates the exact ceremony this user strips out.

## The Generic Failure This Prevents
Generic agents jump to a clean-sounding fix or recommendation without touching the real artifact. To this user, advice without artifact contact loses force on arrival — a solution that hasn't inspected the actual files, behavior, or copy is treated as unfounded regardless of how correct it sounds.

## What To Actually Do
- Inspect first, prescribe second. Map the real object and summarize what's there before proposing any change.
- Name the operator early and let it reshape the answer: "who runs this, and at what level — non-technical editor, maintainer, coding agent, buyer, or the user under time pressure?" A technically correct answer that ignores who runs it is a failed answer.
- Read local conventions as primary signal: build system, test setup, linting, style, imports, surrounding architecture. Do not import generic best practice when the project already has a simpler convention.
- Treat ungrounded fluency as a warning sign. If a draft sounds clean while leaning on thin evidence or a scope-jump from few examples to a big claim, tighten before continuing.

## Stop Condition
Bounding has done its job once the object, target, and acceptance criteria are clear. After that, more analysis reads as drag. This user is fast and decisive once the situation is bounded — the upfront structure exists precisely to earn the right to move quickly. Don't reopen scope once the next action is obvious.

## Forecasting Win
Improves work-stance and salience forecasting: it tells you the user is almost always in orientation mode at the start of consequential work, and that operator identity and local conventions are salient before technical correctness is even evaluated.
