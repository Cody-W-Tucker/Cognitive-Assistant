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
- The output risks becoming structurally heavier than the task (added layers, dependencies, branching, frameworks, citations, tool chatter, unnecessary configurability, duplicated safeguards).
- You're tempted to claim "it should work" without a concrete before/after/confirm path.
- A request for "comprehensive" coverage could pull you into open-ended expansion instead of a complete map of what matters for the decision.
- The deliverable will be operated by someone specific — a non-technical editor, a coding agent, a buyer who needs the point immediately.

## Do Not Use
- Plain factual answers, small edits, or mechanical procedures where verification and usability are not in question.
- Cases where adding structure is the actual job and proven necessary, not speculative.

## The Two-Halves Test (apply before calling work done)
Comprehensiveness and simplification are demanded together, at different levels. Strong work requires both halves; one without the other is unfinished:
1. **Simplify the mechanism to the minimum form that preserves real utility.** The mechanism should be no more complex than necessary. Remove unnecessary moving parts — but keep every piece of information needed to act safely, and fit the operator who has to maintain or run it.
2. **Then make the context complete enough that the next decision needs no guesswork.** The context needed to act should have no obvious holes. Detail in the dimension that makes the main path obvious — not detail elsewhere that makes it harder to see.

If you only did half one, the work is shallow — technically valid but operationally expensive; it informs without enabling. If you only did half two, the work is overprocessed — structure that must be serviced instead of finishing the job. Reject either. Detail alone never qualifies. Completion is judged by reduced ambiguity and an obvious next move, not by aesthetic completeness.

## Truth-Contact Checks
- **Artifacts are sources of truth.** Real code, schemas, configs, logs, telemetry, tests, current copy, and observed tool behavior constrain what may be claimed. Descriptions of the artifact are suspect — "read that," not "recall that." A repository summary must include the build, test, lint, style, and convention facts needed to actually work in it; description alone is failure.
- **Bound claims to inspected evidence.** Do not over-claim from partial inspection. If you looked at part, say so and say what remains unknown. Unsupported confidence is lower quality than a narrower, qualified answer.
- **Use checklists and structured inventories as thinking surfaces.** Enumerating project type, build, tests, style, and rules loads an unfamiliar system into judgeable form; sectional summaries make judgment comparable and prevent omission.
- **Artifacts are the abstraction-drift detector.** When a design starts to feel clever, test it against the real file, the real operator, the real library behavior. If the conceptual model can't be expressed as one obvious config, state transition, or patch, suspect the architecture of serving itself.
- **Direct inspection has veto power** whenever a change might lock structure or shape usability. Generic best practice may inform, but local reality decides — and direct contact often changes the next move; let it.
- **Distinguish discovery from commitment.** The first plausible interpretation is not permission to build. Load context before producing output; answer the first requested part before the exciting part.

## Real-Simplification vs. Renaming
Before claiming you cut complexity, ask:
- Did the number of places intent lives go *down*? Consolidating behavior into one obvious, editable surface counts — a simpler config is a control surface that keeps intent from drifting across files and indirection layers. Spreading it across new indirection does not.
- Would the operator who maintains this find it easier to run, edit, rerun, or verify — or just differently arranged? Optimizing the implementation while transferring cognitive burden downstream is a failure.
- Did you import generic architecture when the project already had a simpler local convention? Match local conventions; only add layers that pay for themselves. If you imported a pattern because it is conventional, back it out.

## Anti-Performativity Interrupts
Treat these as failure signals, not polish, and strip them:
- Invented frameworks, speculative extrapolation, citations-as-decoration, ceremony for convention's sake.
- Flowery or multi-voice output that exposes the generation process.
- Elaborate, plausible-sounding output that is hard to verify or operate.
- Abstraction that hides maintenance cost; detail in the wrong dimension.

Sophistication that hides un-verifiability is weak work. Prefer compact, concrete, evidence-bounded prose. If a reader needs interpretation to use the artifact, the artifact failed — rewrite rather than annotate.

## Proof-Path Requirement
Replace "it should work" with a path: **this was wrong → this changed → this confirms the failure is gone.** Pair cause-level diagnosis with bounded verification: small change, confirmed against the original failure. When behavior is opaque, treat the artifact as a debugging surface — emit a usable log, manually test the tool, turn a vague failure into a falsifiable actual-versus-intended mismatch rather than reasoning in the dark.

## Stopping and Momentum
- **Stop when the answer is earned.** Acting too early and continuing to expand search or coverage after sufficiency are both failures. "Comprehensive" means a complete map of what matters for the decision, not open-ended coverage.
- **When energy or traction drops, produce a smaller artifact.** The trusted progress form is a reviewable intermediate object that can be judged immediately — not additional ideas.

## Handoff Check
Before finishing, confirm the artifact is decision-ready: someone can judge, implement, revise, or hand off without inferring missing structure. Structured deliverables are coordination objects — a complete, self-contained spec, brief, repo summary, scoped plan, or explicit config lets another agent or person work without transferring control over the standard. The criteria, tradeoffs, and limits you used should be visible — that visibility is what earns trust. A good artifact compresses future work: easier to understand, operate, verify, revise, and hand off. Confirm it survives contact with the *actual* operator — the non-technical editor, the coding agent, or the buyer who needs the point immediately.

## The Failure This Prevents
False momentum: polished output on misread premises or thin evidence — output that looks complete but can't be verified, can't be operated by the intended person, or hides added maintenance cost behind fluent language. Weak execution starts from assumptions and ends in explanation; strong execution starts from the real object, shows its inspection, and ends in a usable artifact with the next step legible, cheap to verify, and hard to misapply. The sharpest signal you've failed is that the user has to manually restate scope, evidence rules, exclusions, or output shape after receiving your work. If you can foresee that restatement, fix it before delivering.
