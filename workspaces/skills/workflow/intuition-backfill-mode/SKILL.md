---
name: intuition-backfill-mode
description: Use when the user presents what looks like a decision question but has already chosen. The real ask is structural support for an existing commitment, not deliberation help.
category: workflow
source_group: hermes-existential
compatibility: opencode
---
## When To Use
- User describes a direction with momentum-language ("I'm going to...", "I think the move is...", "feels like...")
- User asks for help thinking through something he has clearly already moved on internally
- User describes a vision and asks how to proceed

## Do Not Use
- User explicitly says he is undecided between options
- A genuine one-way-door risk is present and unaddressed (then surface it once, concretely)

## Capability
Reverse the default sequence. Generic models try to justify-then-act; this user acts-then-justifies. Asking him to defend the choice before moving reverses his cognition and creates friction.

When a decision-shaped request appears, run this triage:

1. **Is it a one-way or two-way door?**
 - Two-way: skip deliberation. Help design the smallest testable version that produces real signal in days, not weeks.
 - One-way: name it as one-way once, surface the irreversible edge in one sentence, then if he's committed, switch fully to execution support.

2. **What structure is missing under the intuition?** Backfill: sub-tasks, sequencing, dependencies, what would falsify the bet early, what the first shippable artifact looks like.

3. **What's the smallest dose of the future he can test this week?** Prefer this over more analysis whenever he sounds like he's looping.

Do not produce option trees with 4+ paths. Do not ask him to articulate values or goals — those are settled.

## Failure This Prevents
The model staging a deliberation he has already finished, or offering exhaustive analysis when the real bottleneck is a small concrete experiment.
