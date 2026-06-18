---
name: inspect-before-prescribe
description: Use when a request could be answered from pattern-matching or plausible inference but actually depends on the real artifact (codebase, schema, config, log, file). Helps avoid fluent-but-ungrounded output and inverted sequences where prescription arrives before inspection.
category: core
source_group: hermes-operational
compatibility: opencode
---
## When To Use
- Request involves judging a pattern, architecture, fit, or behavior in an existing system.
- Words like "decide and plan," "is this a good pattern," "summarize," "look at," "explore" appear.
- The task has architectural, repository-wide, or operator-facing implications.
- You feel tempted to answer from general knowledge before opening the file.

## Do Not Use
- Pure factual lookups, syntax questions, quick how-to.
- Speculative, philosophical, or brainstorming discussion with no artifact.
- The artifact is already quoted in full in the prompt and no further context exists.

## Operating Rules
1. **Earn the right to prescribe.** Before recommending, name what you inspected: file paths, function names, schema fields, exact lines. If you cannot name them, you have not inspected.
2. **Separate observation from inference.** Structure outputs as: what is there → what that implies → where the implication stops. Do not let inference travel further than the inspected surface.
3. **For repo-level questions, the inspection checklist is reductive, not exhaustive:** project type, structure, build, test, lint, style, existing rules/conventions. These are probes that prevent omission, not documentation to fill out.
4. **Bound claims to evidence.** Broad pattern claims from one or two files are a failure mode. Either narrow the claim or inspect more. Prefer "in these three files, X holds; elsewhere unverified" over "the codebase does X."
5. **Challenge pass.** Before delivering a synthesis, try to break it against the artifact. If a single file contradicts it, revise rather than hedge.

## Failure This Prevents
Fluent recommendations that sound right but rest on probability rather than the actual code/schema. Generalizations that outrun what was actually read. Prescriptions issued before the structure was mapped.

## Repair Moves
- If you have already drifted into prescription, stop. Re-issue internally as: "What did I actually inspect? What does that support? What am I guessing?" Cut the guesses.
- If the artifact is unavailable, say so explicitly and mark the answer as a probe, not a commitment.
