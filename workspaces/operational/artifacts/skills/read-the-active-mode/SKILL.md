---
name: read-the-active-mode
description: Use when it's unclear whether the user wants exploration, planning, execution, diagnosis, or refinement, and answering in the wrong mode would feel premature or off. Helps you resequence instead of charging ahead. Not needed when the requested action and acceptance criteria are already explicit.
source_group: group-2
compatibility: opencode
---
## When To Use
Load when a request could be answered several ways and choosing wrong would violate sequence integrity — e.g. recommending before inspecting, implementing before understanding, or answering the exciting part before the first requested step.

## Do Not Use
Skip when the verb and target are already concrete ("rewrite this," "add X," "search for Y") with clear acceptance criteria. There, more framing is overhead; just execute.

## The Generic Failure This Prevents
Getting ahead of the work. Generic agents reward speed and completeness, so they recommend before inspecting, gather more context after the answerable core is already visible, or hand back a fluent summary with no operational consequence. The objection here is to ungrounded speed, not to difficulty.

## Mode Signals To Read
The user signals the active mode through verbs:
- Plan-first verbs — *look, decide, plan, explore, understand* — mean orientation or fit judgment; don't jump to output.
- Act-now verbs — *rewrite, add, search, note, make, treat this like* — mean execution; don't hand back another framework.
- Behavior diverging from intent means diagnosis: separate actual vs. expected, find the precise cause, validate the repair.
- An artifact that exists but doesn't carry the point means refinement: tighten copy, cut moving parts, sharpen fit.

## Thresholds That Shift The Mode
- Roughness is fine during scouting — approximate is acceptable while only reducing uncertainty or finding candidates.
- Roughness stops being acceptable at handoff — once output must guide implementation, sales, a non-technical user, or a later agent, clarity and completeness become non-negotiable.
- Stop exploring once evidence supports a bounded move. More search after the core is visible is a breakdown, not thoroughness.
- Simplification is a standing override that can interrupt any mode when the surface feels heavier than the job deserves.

## Repair Moves
When you've gotten ahead of the work, resequence explicitly rather than apologize: "look first," "answer this one first," "decide and plan first." When exploration keeps expanding, stop broad search, use the strongest candidates, synthesize, move on.

## What Never Shifts
Control of the standard. The user delegates scouting, retrieval, and execution, but task framing, proof thresholds, and final synthesis stay with them. Don't quietly take over strategy.

## Forecasting Win
Improves work-stance and sequence forecasting: it lets you infer the user's current stance from their verbs and the task's threshold, and identify which move would be premature versus warranted right now.
