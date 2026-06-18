---
name: bind-to-operator
description: Use when evaluating whether a pattern, artifact, or piece of copy is good. Helps replace abstract quality judgments with fit-to-named-operator judgments, and prevents "correct but unusable" outputs.
category: operator
source_group: hermes-operational
compatibility: opencode
---
## When To Use

- Judging whether a pattern, schema, prompt, or UI is "good."
- Producing copy, instructions, or specs that another party (buyer, non-technical editor, coding agent) must act on.
- A request implicates a specific human or agent downstream, even if not stated.
- You catch yourself evaluating elegance, completeness, or best-practice conformance in the abstract.

## Do Not Use

- Internal tooling with only the author as user.
- Pure factual answers with no downstream artifact.

## Operating Rules

1. **Name the operator first.** Before judging, identify who must use, run, edit, or recognize this. Non-technical schema editor? Coding agent reading a spec? Buyer scanning a landing page? Engineer maintaining a service? The judgment criterion changes with each.
2. **Simulate them moving through it.** Walk the artifact from their position. Where do they stall? What do they have to infer? What would they get wrong on first read?
3. **"Done" is operator-defined, not form-defined.**
   - A summary is done when it drives the next action, not when it covers the topic.
   - Copy is done when the next action is obvious, not when it is correct.
   - A spec is done when the executing agent cannot misinterpret it, not when it is comprehensive.
   - A repo summary is done when build/test/lint/style/rules are listed, not when it is well-written.
4. **Reject elegance that costs operator clarity.** If a pattern is clean for the engineer but opaque for the schema editor, it fails. The judgment lives at the harder end.

## Failure This Prevents

Outputs that complete the form of the task (look like a summary, read like a fix, sound like copy) without doing the operational work. Patterns judged elegant by the code but unusable by the actual person who has to fill the form.

## Repair Moves

- If a judgment feels abstract, restate it as: "For [named operator] doing [specific action], does this work?"
- If you cannot name the operator, ask. Do not infer one to keep moving.
