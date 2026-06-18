---
name: collapse-unearned-complexity
description: Use when a solution is directionally right but heavier than the job deserves, or when engineering ceremony is accumulating without clear payoff. Helps you cut layers without underbuilding. Not needed when the structure is already minimal or the complexity is demonstrably load-bearing.
category: workflow
source_group: hermes-operational
compatibility: opencode
---
## When To Use
Load when abstraction, configurability, helpers, defensive checks, extra files, or branching are piling up, or when the implementation starts to feel harder to reason about than the problem itself. This is a standing override — it can interrupt momentum at any point.

## Do Not Use
Skip when the structure is already lean, or when removing a layer would drop context needed for correct action. The goal is the smallest form that still supports correct action — not minimalism for its own sake.

## The Generic Failure This Prevents
Importing elegance, generality, and future-proofing as if they were virtues. To this user they're suspect until they earn their place; generic systems overweight polish, comprehensiveness, and sophisticated architecture. Hidden maintenance cost — layers and dependencies added before need is proven — is weak execution.

## How To Cut
- Ask what each layer buys. "Why can't this config be hardcoded values? Why does this factory need an if-tree if the types already encode behavior? Why keep local error handling if the library already covers it?"
- Consolidate behavior into one obvious, editable place. A simpler config is a control surface — it keeps intent from drifting across files and indirection layers.
- Push back practically, not managerially: "this layer doesn't seem to buy enough — can we collapse it?" Earn trust by removing moving parts, not by demonstrating sophistication.
- Test abstractions against the real object: if an abstraction can't be explained through the actual files, fields, behavior, or workflow, it loses credibility.

## The Reconciling Rules
This user asks for both full survey and aggressive simplification. Reconcile them: comprehensive enough to orient, simple enough to operate. "Comprehensive" is instrumental — the orientation pass that lets them narrow, not an end in itself. Likewise, keep the structure that reduces ambiguity (small diffs, post-change checks, testable steps) and cut only structure that survives by convention alone.

## Boundary Conditions
- Strongest where results get implemented, navigated, or acted on: codebase exploration, architecture/config decisions, debugging, design review, prompt and agent work, lead enrichment and sales rewriting.
- Relaxes for simple lookups and one-off questions — don't impose a tightening loop there.
- Drops away in open-ended philosophical or phenomenological exploration, where constraint-seeking and artifact-anchoring don't apply and approximation is permitted. Don't force this pattern onto unbounded, non-artifact work.

## Forecasting Win
Improves salience and threshold forecasting: complexity creep is the primary threat this user notices first, and this skill tells you when collapsing the surface restores momentum versus when cutting would underbuild.
