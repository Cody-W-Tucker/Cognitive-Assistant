---
name: handoff-without-residue
description: Use when output will be executed, followed, or persuaded by someone else — another human, an agent, or a buyer. Not needed for throwaway exploration or internal probes.
source_group: group-4
compatibility: opencode
---
## When To Use
Load at the handoff point: writing a spec for an agent, copy for a buyer, a workflow for a non-technical editor, or any artifact someone else has to act on without you in the loop. Polish matters here and almost nowhere else.

## Do Not Use
Skip during reconnaissance, debugging probes, or rough drafts that only you will use. Tightening wording before handoff is wasted effort and reads as elegance-for-its-own-sake.

## What This Prevents
Process leak — output that exposes seams, tool chatter, citations, invented frameworks, or references to the interaction itself, forcing the next operator to adapt to your logic instead of acting. Also the happy-path artifact that works in the demo but fails on missing state, preconditions, or the operator's actual level of skill.

## Handoff Checks
- Strip process exhaust: no citations, file/line clutter, tool chatter, or meta-references. The artifact should be evaluable quickly for substance, scope, and honesty.
- Make it self-contained: a brief should transfer execution without needing further clarification. The artifact carries the intent so collaboration doesn't require shared strategy authorship.
- Judge against the real operator, not abstract correctness. "Is this a good pattern for a non-technical person?" is the gate.
- Tighten wording toward "easier to act on," never toward flair.
- Cover the relevant failure cases, not just the happy path — missing state, preconditions, the operator's actual usage level.

## Authority Boundary
Offer options and tradeoffs; don't claim the direction. Framing, proof thresholds, and final synthesis stay with the user. Initiative that bounds the task helps; initiative that expands scope intrudes. Execute bounded operations well and hand back legible work.
