---
name: bound-before-solving
description: Use before solving to inspect the real object and bound what can safely be claimed. Owns pre-solution contact only, not diagnosis or verification.
category: core
source_group: hermes-operational
compatibility: opencode
---

## When To Use
Load this before solving when the task has enough weight that an answer produced from memory or pattern-matching would be unearned. The job is to make first contact with the real object: the code, prompt, schema, artifact, user workflow, buyer context, or acceptance threshold.

Use it to bound the work before any recommendation, design, rewrite, implementation plan, or judgment. This skill ends once the relevant object has been inspected and the limits of the claim are clear.

## Do Not Use
Do not use this to diagnose a known failure, choose the user's operating mode, simplify a system, force a decision, or prove that a completed change worked. Use the neighboring skill that owns that later step.

## What To Do
- Touch the real object before prescribing: inspect the file, behavior, artifact, source material, or workflow that the answer depends on.
- Name the operator only enough to bound the work: who uses, accepts, maintains, or is affected by the result?
- Name the acceptance threshold only enough to know what evidence would matter.
- Separate what was observed from what is inferred. If contact is partial, say so plainly.
- Prefer the local convention over imported best practice unless the local convention is itself the object under inspection.

## Output Shape
Return the boundary: what was inspected, what is now safe to claim, what remains unknown, and the smallest next step unlocked by that contact.
