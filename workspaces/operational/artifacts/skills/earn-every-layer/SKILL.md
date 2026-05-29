---
name: earn-every-layer
description: Use when the response, design, or fix risks becoming structurally heavier than the job needs — extra files, abstraction, defensive scaffolding, frameworks, or polish. Not needed when the structure is already minimal or when entering an unfamiliar system that genuinely needs a full map.
compatibility: opencode
---
## When To Use
Load this when you notice yourself adding structure: a config layer, a factory, a branching tree, redundant error handling, a new file, an option framework, citations, or tooling commentary. This user notices complexity that exceeds the task before he evaluates whether it works — overbuilt structure registers as drag almost immediately.

## Do Not Use
Do not use this to do less or to ship minimal-compliance fixes. He rejects half-fixes as hard as he rejects overbuilding. Also skip when first entering an unfamiliar codebase — there he wants a full structural map; breadth for orientation is correct. The target is convention-driven complexity, not structure itself.

## The Test For Each Layer
For every file, abstraction, safeguard, or indirection, ask: does this earn its complexity with visible operational payoff, or is it here by convention? If by convention, strip it.
- A function store that could be a hardcoded config — collapse it.
- Branching logic that type information already determines — let the types carry it.
- Local error handling the library already covers — remove it.
- Separate files where separation buys nothing — merge them.

## Prefer The Inspectable Form
Push important behavior into one obvious, editable place — a config file, an explicit default — so intent cannot drift across indirection. The goal is legibility: a working surface small enough to judge directly and reverse without rediscovering its logic.

## Watch For Overprocessing
Comprehensiveness, polish, architectural elegance, and tooling chatter read as noise to this user unless they earn their place. "False sophistication that is harder to reason about than the problem" is a defect, not a strength. If a clever config or summary feels too clever, that gap is a signal the abstraction has overreached.

## Rigor At Commitment
Simplify freely in reversible discovery and rough drafts. But once a change is structural or irreversible, raise the bar: the simplest form still has to be a proper fix, durable, and correct — not just the smallest.

## Failure This Prevents
Complexity overrun and overprocessing: producing technically complete but operationally heavy work that is correct, elaborate, and hard to run or hand off.
