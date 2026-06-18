---
name: earn-every-layer
description: Use when work is directionally right but risks becoming structurally heavier than the job — added abstraction, config layers, or defensive scaffolding. Not needed when standard scaffolds genuinely keep work small and testable.
category: workflow
source_group: hermes-operational
compatibility: opencode
---
## When To Use
Load when you notice ceremony accreting: a config that "seems overly complex," an abstraction layer, a function store where a flat file would do, error handling the library already covers, or branching the type system makes unnecessary. Also when energy or momentum has dropped and the problem feels uncontrollable.

## Do Not Use
Don't strip for its own sake. This user readily adopts MVP, small diffs, and post-change checks — scaffolds that keep work small and testable earn their keep. The target is unjustified structure, not all structure. And don't apply this to comprehensive codebase summaries: there, completeness means "all the facts needed to act," which is not the same as overbuilding.

## What This Prevents
Overbuilt output that adds ceremony before value and is harder to operate than the problem requires. Also the live failure mode where conceptual fluency stalls the actual deliverable — insight that never becomes executable structure.

## The Test For Each Layer
Ask of every surviving piece: does this materially improve clarity or control, or does it survive only by convention? "This could just be a config file" is the canonical collapse move. Standards survive on payoff, not on being standard.

## Compression Under Pressure
Recovery here is constraint, not expansion: reduce scope, hardcode where safe, compress language, make the next step obvious. When stuck, shrink the problem to something inspectable — a hardcoded config, a scoped checklist, a concrete inventory. A crisp intermediate object proves the work is controllable again.

## Forcing The Executable Step
If the user is circling in the conceptual layer, don't mirror it back. Translate insight into structured inputs and concrete commands. Pair every interesting idea with the smallest runnable next move.

## Reversibility Boundary
Roughness is fine while the move is reversible — sketchy setups, temporary UI, "for now" scaffolding during exploration. The bar rises sharply the moment a choice becomes structural: core config, infrastructure, repeated workflows, operator-facing interfaces.
