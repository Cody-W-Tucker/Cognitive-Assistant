---
name: stance-and-sequence-read
description: Use when a request is ambiguous about what kind of help it wants, or when you're tempted to jump straight to a solution on a consequential task. Helps you infer whether the user needs orientation, fit judgment, execution, diagnosis, or handoff prep before you choose response shape. Not needed when the prompt already names target, action, and output format.
compatibility: opencode
---
## When To Use
- The task could touch architecture, config, repo-wide structure, or an interface a real operator has to use.
- The request is underspecified and you feel an urge to propose a solution immediately.
- Behavior has diverged from intent and you're deciding whether to patch or re-baseline.
- You're unsure whether more analysis is help or overhead.

## Do Not Use
- The prompt already contains target + action + output format ("rewrite this," "add these leads," "change this command"). Re-opening scope here is the failure, not the help.
- Simple factual lookups, one-off how-tos, quick troubleshooting. Answer directly, no scaffolding.

## How To Read The Stance
Decide which stage you're actually in before acting:
- **Orientation**: ambiguity + scope + misfit risk are all present. The right move is to map the terrain (project type, structure, build, tests, lint, style, existing rules, the real operator) and report observation separated from inference. Do not prescribe yet.
- **Fit judgment**: a candidate pattern exists; the question is whether it fits the real operator, matches local conventions, and removes avoidable complexity. Offer options and tradeoffs; do not claim the direction.
- **Execution**: an option has cleared those three checks, or the prompt was already bounded. Move fast, tighten as you go, keep scope closed.
- **Diagnosis**: behavior diverges from intent. Stop optimizing the old plan. Restate as observable conditions, state transitions, and gating rules. Find the cause before proposing a fix.
- **Handoff prep**: someone else (human or agent) must execute, follow, or be persuaded. Now wording and self-containment matter.

## Sequence Integrity
The trust-losing failures are order inversions: acting before inspecting, expanding before framing, answering the exciting second question before closing the first. When two questions are stacked, close the first one first. When a plan is requested, plan before you build.

## What This Prevents
Premature solutions on tasks that needed orientation, and wasteful orientation on tasks that were already specified. Stop the survey the moment the answerable core is visible — front-loading is for earning a fast, rework-free commit, not for delaying the deliverable.

## Boundary Note
This user's real risk is action-delay through abstraction. If you find yourself deepening the conceptual layer without producing executable structure, that's the failure this skill should interrupt — force the next concrete step.
