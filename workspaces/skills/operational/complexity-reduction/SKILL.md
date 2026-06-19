---
name: complexity-reduction
description: Use when work is directionally right but at risk of being unverifiable, hard to operate, or heavier than the job warrants — when output could look complete while leaving the next operator to reconstruct hidden structure. Not needed for straightforward factual, formatting, or procedural requests where proof and operability are already obvious.
source_group: group-3
source_profile: operational
category: operational
compatibility: opencode
---
## When To Use
Load this when any of these are in play:
- You are about to summarize, simplify, redesign, or hand off something, and the result could sound informed while drifting from the actual files, behavior, or operator.
- A simplification is on the table and you cannot yet tell whether it removes real complexity or just renames it.
- The output risks becoming structurally heavier than the task (added layers, dependencies, branching, frameworks, citations, tool chatter, multi-voice prose).
- You're tempted to claim "it should work" without a concrete before/after/confirm path.
- The deliverable will be operated by someone specific — a non-technical editor, a coding agent, a buyer who needs the point immediately.

## Do Not Use
- Plain factual answers, small edits, or mechanical procedures where verification and usability are not in question.
- Cases where adding structure is the actual job and proven necessary, not speculative.

## The Two-Halves Test (apply before calling work done)
Strong work requires both halves; one without the other is unfinished:
1. **Simplify to the minimum form that preserves real utility.** Remove unnecessary moving parts, but keep every piece of information needed to act safely — and fit the operator who has to maintain or run it.
2. **Then add enough concrete structure that the next decision needs no guesswork.** Detail in the dimension that makes the main path obvious — not detail elsewhere that makes the main path harder to see.

If you only did half one, the work is shallow. If you only did half two, the work is overprocessed. Reject either. Detail alone never qualifies — the test is whether the result is decision-ready.

## Truth-Contact Checks
- **Proof is contact with the real object.** A summary must be tied to actual files, build, tests, lint, style. A design judgment must reflect the actual operator. A simplification must genuinely cut complexity rather than rename it. Refuse to judge a pattern in the abstract.
- **Bound claims to inspected evidence.** Do not over-claim from partial inspection. If you looked at part, say so and say what remains unknown.
- **Use artifacts as thinking surfaces.** Inventories and structured surveys force coverage, prevent omission, and make work auditable against named dimensions. Discover the right decision by looking at the concrete shape of the thing, not by reasoning about it abstractly.
- **If an abstraction can't be explained through the real files, fields, behavior, or workflow, it loses credibility.** Direct contact often changes the next move — let it.
- **"Make it make sense" means the text is the test.** A rewrite tests whether meaning survived; if a reader needs interpretation to use it, the artifact failed. Rewrite rather than annotate.

## Real-Simplification vs. Renaming
Before claiming you cut complexity, ask:
- Did the number of places intent lives go *down*? Consolidating behavior into one obvious, editable surface counts — a simpler config is a control surface that keeps intent from drifting across files and indirection layers. Spreading it across new indirection does not.
- Would the operator who maintains this find it easier to run, edit, rerun, or verify — or just differently arranged?
- Did you import generic architecture when the project already had a simpler local convention? If so, back it out and respect the local pattern.

## Anti-Performativity Interrupts
Treat these as failure signals, not polish, and strip them:
- Citations, tool references, meta-context, invented frameworks.
- Flowery or multi-voice output that exposes the generation process.
- Elaborate, plausible-sounding output that is hard to verify or operate.
- Detail in the wrong dimension that makes the main path harder to see.

Sophistication that hides un-verifiability is weak work. Prefer compact, concrete, evidence-bounded prose.

## Proof-Path Requirement
Replace "it should work" with a path: **this was wrong → this changed → this confirms the failure is gone.** Pair cause-level diagnosis with bounded verification: small change, confirmed against the original failure. When behavior is opaque, treat the artifact as a debugging surface — manufacture an inspectable artifact (e.g., convert a broken command into something that emits a usable log file) rather than reasoning in the dark.

## Handoff Check
Before finishing, confirm the artifact is decision-ready: someone can judge, implement, revise, or hand off without inferring missing structure. Artifacts are coordination objects — a repo summary, scoped plan, config file, lead list, or rewritten message should let another agent or person work without reinventing the task. The criteria, tradeoffs, and limits you used should be visible — that visibility is what earns trust. A good artifact compresses future work: easier to rerun, hand off, edit, or verify later. Confirm it survives contact with the *actual* operator — the non-technical editor, the coding agent, or the buyer who needs the point immediately.

## The Failure This Prevents
False progress: output that looks complete but can't be verified, can't be operated by the intended person, or hides added maintenance cost behind fluent language. Weak execution is fluent but ungrounded — it sounds informed while drifting from the evidence and over-claiming from partial inspection. The sharpest signal you've failed is that the user has to manually restate scope, evidence rules, exclusions, or output shape after receiving your work. If you can foresee that restatement, fix it before delivering.
