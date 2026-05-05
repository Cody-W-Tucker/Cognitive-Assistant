---
name: collapse-toward-config
description: Use when a proposed or existing solution is growing factories, branches, indirection, configurable layers, or defensive scaffolding that has not visibly earned its cost. Helps choose the simplest explicit structure that still does the job for the named operator.
compatibility: opencode
---

## When To Use

- You are about to introduce a factory, registry, strategy pattern, plugin layer, or "configurable" abstraction.
- The code under review has if-trees that re-encode information already present in types or schema.
- A non-technical operator (someone editing a schema, filling a form, running a script) will touch this.
- The phrase "seems overly complex" or "can it just be..." would reasonably apply.

## Do Not Use

- Genuinely dynamic requirements with proven runtime variability.
- Established project conventions already use the heavier pattern — match the codebase first.
- Safety, compliance, or security domains where the scaffolding is load-bearing.

## Decision Heuristics

1. **Default to hardcoded config.** A working config a person can edit beats a flexible system that requires explanation. Start there; add indirection only when a concrete second case forces it.
2. **Abstraction must earn its keep.** For each layer, name (a) the concrete second use case it serves today and (b) what breaks without it. If neither answer is sharp, delete the layer.
3. **Types over branches.** If the type system already encodes the discriminator, an if-tree is redundant. Dispatch through the type or collapse to a flat map.
4. **Prefer fewer files.** A new file boundary should match a real seam, not a stylistic instinct. Inline first; split when a real consumer appears.
5. **Defensive code only after a real failure.** Try/except, fallbacks, and null guards added "just in case" are drag. Add them in response to an observed failure mode.

## Compression Test

Before finalizing structure, ask:

- Could the named operator open one file and understand the whole behavior?
- Is every surviving piece doing visible operational work?
- Would removing this layer break a real, named use case — or only a hypothetical one?

## Failure This Prevents

Technically correct, architecturally tidy code that is operationally heavy: extra files, hidden behavior, abstractions defending against problems that do not exist, structures the actual operator cannot navigate.

## Repair Moves

- Reframe: "Treat this like a hardcoded config, not a function store."
- Name the simpler model out loud: "This is X, not Y."
- Delete one layer and see if anything real breaks. If not, the layer was drag.
