---
name: diagnose-before-patching
description: Use when something is broken or failing and the cause must be found before changing it. Owns failure diagnosis only.
category: core
source_group: hermes-operational
compatibility: opencode
---

## When To Use
Load this only when something is broken, failing, regressing, contradictory, or behaving differently from the stated expectation. The skill owns cause-finding before repair.

Use it for build failures, runtime errors, test regressions, bad outputs, broken prompts, unreliable workflows, or operational symptoms where a patch would otherwise be a guess.

## Do Not Use
Do not use this for ordinary pre-solution inspection, stylistic refinement, packaging a decision, simplifying a design, or proving a completed fix. If there is no failure state or symptom, this skill is too heavy.

## What To Do
- State the observed failure and the expected behavior in concrete terms.
- Reproduce or localize the symptom before changing anything when feasible.
- Trace from symptom to likely cause using the smallest useful evidence: logs, tests, diffs, inputs, config, or runtime behavior.
- Change only what the cause explains. Avoid broad rewrites that merely pass near the symptom.
- If the cause remains uncertain, label the patch as provisional and keep the next check narrow.

## Output Shape
Return the failure, evidence, likely cause, minimal patch, and the targeted check that would prove the cause was addressed.
