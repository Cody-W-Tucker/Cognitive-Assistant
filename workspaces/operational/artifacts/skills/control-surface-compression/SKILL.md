---
name: control-surface-compression
description: Use when a solution, artifact, or explanation risks becoming structurally heavier than the job or too expensive for the next operator to use.
compatibility: opencode
---
## When To Use
Use this when work is directionally correct but has too many layers, files, abstractions, options, words, checks, or hidden assumptions for the actual task.

This applies to code structure, configs, page-building patterns, automations, schemas, guides, copy, lead workflows, and handoff artifacts.

## Do Not Use
Do not use when complexity is clearly required by scale, safety, performance, team conventions, compliance, or a known future extension. Do not flatten structure just to make something shorter.

## Failure This Prevents
Prevents operational drag: technically acceptable work that is hard to inspect, maintain, hand off, edit, debug, or use because the control surface is larger than the problem.

## Compression Heuristic
Every surviving layer should earn its place by improving at least one of:

- legibility
- maintainability
- user operability
- verification
- reuse that is actually needed
- alignment with local conventions
- reduction of future errors

If a layer does not visibly buy one of these, collapse it.

## What To Collapse First
Look for removable weight in this order:

1. Redundant wrappers around library behavior.
2. Factories or stores with only one real consumer.
3. Split files that obscure rather than clarify.
4. Config indirection where a small hardcoded config is easier to inspect.
5. Duplicate validation or fallback logic already handled elsewhere.
6. Generalized options not needed by the current operator.
7. Dense wording that requires interpretation before action.

## Preferred Control Surfaces
Prefer one obvious place to inspect or edit:

- a small config object over scattered constants
- a direct component pattern over a meta-framework
- explicit defaults over implicit fallback chains
- a concise schema over prose-only rules
- one task record over hidden conversation context
- clear copy with one next action over polished but indirect language

## Operator-Fit Checks
Before finalizing, ask who must operate the result:

- **Nontechnical user**: Can they make the intended change without understanding internals?
- **Maintainer**: Can they find the source of behavior quickly?
- **Coding agent**: Is the next action explicit and bounded?
- **Buyer / reader**: Is the pain point and next step obvious?
- **Future self**: Is there one inspectable surface rather than many hidden dependencies?

If the answer is no, simplify the interface or handoff rather than adding explanation around the complexity.

## Simplification Without Losing Utility
Do not remove necessary detail. Compress by making the work more inspectable:

- replace broad categories with concrete fields
- replace multiple paths with the supported path
- replace vague instructions with checklists or acceptance criteria
- replace clever abstraction with local convention
- replace long prose with sequence: context, action, proof, next step

## Review Output Shape
When applying this skill, report briefly:

1. What was too heavy.
2. What was collapsed or centralized.
3. What capability was preserved.
4. What tradeoff remains, if any.
