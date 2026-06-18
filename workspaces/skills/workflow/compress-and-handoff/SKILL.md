---
name: compress-and-handoff
description: Use when output will be read for a decision, or when another human or agent must execute from what you hand back. Helps you strip process exhaust, tighten wording only where it must be acted on, and package work as a self-contained brief that needs no further clarification. Not needed for throwaway exploration notes or quick interactive back-and-forth.
category: workflow
source_group: hermes-operational
compatibility: opencode
---
## When To Use
- Someone else must follow, execute, or be persuaded by the output (a spec for an agent, instructions for a non-technical operator, copy for a buyer, a workflow for a non-technical editor).
- You're finalizing a summary or recommendation meant to drive a decision.
- You catch yourself including citations, file/line refs, tool chatter, or references to the conversation itself.

Polish matters here and almost nowhere else.

## Do Not Use
- Mid-exploration, reconnaissance, or debugging probes, where rough notes are fine and polishing is premature overhead.
- Rough drafts only you will use — tightening wording before handoff reads as elegance-for-its-own-sake.
- Tight interactive loops where the user is steering turn by turn — don't formalize what's still in motion.

## Strip Process Exhaust
Remove anything that forces the reader to adapt to your logic rather than judge the substance: citations, file/line breadcrumbs, tool narration, performative rigor, invented frameworks, multi-voice or flowery phrasing, and references to prior or future turns. The artifact should be evaluable quickly for substance, scope, and honesty.

## Compression Rule
Tighten language toward "easier to act on," never toward elegance or flair. If wording doesn't make sense, rewrite for clarity and a more obvious next action — don't add flourish. Keep the important structure easy to understand and the next move obvious.

## Handoff Brief Check
When handing off execution, make the artifact carry the intent so collaboration doesn't require shared strategy authorship. The brief should include: what to do, the boundary (what to exclude), the success threshold or proof bar, and the intended operator. A self-contained brief transfers execution without needing further clarification — if the receiver would have to come back and ask, it isn't done.

## Verify Against the Real Operator
- Judge against the actual operator, not abstract correctness. "Is this a good pattern for a non-technical person?" is the gate.
- Cover the relevant failure cases, not just the happy path — missing state, preconditions, and the operator's actual usage level. The demo-only artifact that breaks on missing state is the failure mode to catch.

## Retain Framing, Delegate Execution
When you hand bounded operations to sub-agents or helpers (scout, retrieve, test), keep the task framing, proof threshold, and final synthesis under your control. Offer options and tradeoffs; don't claim the direction. Initiative that bounds the task helps; initiative that expands scope intrudes. Authority over direction stays with the user.

## What This Prevents
Process leak — output that exposes seams and forces downstream humans to reconstruct hidden reasoning, or that exposes tool chatter, citations, and invented frameworks that make the next operator adapt to your logic instead of acting. Also over-polished prose that reads elaborate but weak, and handoffs that stall because the receiver needs more context. The win is an artifact someone can run, verify, or reuse without you in the room.
