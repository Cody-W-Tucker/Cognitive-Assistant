---
name: artifact-proof-bounds
description: Use when a recommendation, diagnosis, or summary risks drifting away from the actual artifact or outrunning inspected evidence.
compatibility: opencode
---
## When To Use
Use this when the work depends on real files, schemas, logs, UI behavior, drafts, lead records, commands, configs, or other concrete artifacts.

This is especially useful before architectural advice, implementation plans, bug fixes, repo summaries, copy revisions, or business recommendations where unsupported plausibility would create rework.

## Do Not Use
Do not use for simple factual questions, clearly hypothetical brainstorming, or cases where the user explicitly asks for a rough answer without artifact inspection.

## Failure This Prevents
Prevents fluent but ungrounded output: claims that sound reasonable but do not touch the actual source material, local conventions, current behavior, or proof threshold.

## Truth-Contact Test
Before making a consequential claim, identify what it is grounded in:

- **Code**: files inspected, relevant functions/components, commands, tests, linting, build setup, existing patterns.
- **Bug behavior**: observed symptom, reproduction path, expected behavior, actual behavior, logs/errors, state transitions.
- **Copy or docs**: exact wording, intended reader, next action, confusing sequence, density or ambiguity.
- **Business / leads**: concrete company facts, buyer pain, fit reason, outreach angle, missing evidence.
- **Workflow / automation**: current process, operator, inputs, outputs, failure points, maintenance surface.

If you cannot name the artifact basis, avoid firm recommendations.

## Evidence-Bounded Claims
Use claim strength that matches inspection depth:

- **Directly inspected**: “This file does X,” “The current command is Y,” “The copy buries the next action after Z.”
- **Inferred from inspected context**: “This likely exists because...,” “The surrounding pattern suggests...”
- **Unverified**: “I have not confirmed X,” “This would need checking in Y before changing.”

Do not convert inference into fact.

## Inspection Before Prescription
When stakes are non-trivial:

1. Locate the real object.
2. Inspect the smallest useful context window.
3. Identify local constraints and conventions.
4. Make the narrowest supported recommendation.
5. Stop when there is enough evidence for the next decision.

Avoid exhaustive research unless the decision requires it.

## Reversible Probe Default
When context is incomplete but action is useful, prefer reversible probes:

- search before edit
- inspect before refactor
- patch the smallest surface
- test the original failure
- label assumptions explicitly

## Grounded Response Shape
For consequential answers, include:

1. **What I inspected**
2. **What that shows**
3. **What I recommend or changed**
4. **What remains unverified**, if anything

Keep this concise. The point is proof contact, not ceremony.

## Red Flags
Interrupt the response if you notice:

- recommending a library, abstraction, architecture, or rewrite without seeing the current setup
- summarizing a repo without build/test/lint/style facts when those matter
- diagnosing a bug from the symptom alone
- producing polished copy without accounting for the reader’s next action
- giving broad business advice without concrete buyer pain or fit evidence
