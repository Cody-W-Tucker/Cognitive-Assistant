---
name: scope-framing
description: Use when a task carries design, implementation, or judgment weight and the obvious move is to start solving before the object, operator, and acceptance criteria are pinned down. Not needed for straightforward factual, formatting, or well-bounded procedural requests.
source_group: group-1
source_profile: operational
category: operational
compatibility: opencode
---

# Scope Framing

## When To Use

Load this when the request could be answered immediately but answering early would commit effort around hidden scope, hidden assumptions, or an unnamed operator. Typical triggers:

- A fix, recommendation, or design is asked for before the real artifact (codebase, component, schema, prompt, copy, lead, runtime behavior) has been looked at
- The task names a goal but not who has to run, maintain, or live with the result
- The work could expand indefinitely (configurability, layers, defensive checks, exhaustive discovery) with no clear stop condition
- A request sounds clean but leans on thin evidence or a jump from a few examples to a broad claim
- A messy, expert-dependent domain needs to become runnable machinery — structured workflow, simpler config, guided interface — rather than knowledge stuck in heads or chat
- Prompt mode is ambiguous: plan-first verbs mixed with act-now pressure

## Do Not Use

- Object, target operator, and acceptance criteria are already clear — more framing is drag; execute
- Small, bounded, factual or mechanical tasks — short question, direct answer, no discovery pass
- Planning would be ritual rather than reducing real ambiguity or architectural risk
- Known failure mid-fix — use `failure-recovery` / diagnose path
- Work already at handoff of a finished artifact — use `boundary-handoff`
- Mechanism already overbuilt and the job is collapse — use `complexity-reduction`

## What Is Being Protected

Not correctness in the abstract — **decision-quality under real operating conditions**: usability, legibility, and fit for the person or system that will actually run the output.

Structure is valued when it makes work inspectable; simplification is valued when it lowers hidden operating cost; detail is valued only when it changes the decision. Against: unearned depth, ungrounded planning, abstraction that stops the work from being directly understood, changed, or handed off.

He is not a planner by disposition. Once ambiguity is locally bounded and the next move is obvious, further analysis reads as friction. Scope framing exists to earn the right to move fast afterward — not to perform process.

## Read Prompt Mode First

- **Plan-first verbs:** look, decide, plan, explore, understand, summarize → orientation / fit; map before claim; no implementation until fit is explicit
- **Act-now shape:** imperative + embedded deliverable + acceptance already collapsed ("rewrite this to make more sense," "add these as leads, note the pain") → execute; do not reopen scope with a discovery ceremony
- **Ambiguous:** one question only if needed — is this discovery or commitment? — then move

Misreading mode is the fastest way to create friction: discovery theater on an act-now ask, or premature build on an explore ask.

## Framing Sequence (Bound, Don't Solve)

On consequential work, first move is not the solution:

1. **Name the object**
   Touch the real artifact before prescribing. Summarize what is actually there (files, behavior, copy, schema, tool output). Do not trust a fix that has not made contact. Abstract advice without artifact contact loses force.
   - Unfamiliar system checklist (comprehensive-enough to orient, not open-ended): project type, directory structure, key files, build, tests, lint, style, existing rules/instructions, current workflow.
   - "Comprehensive" = complete map of what matters for the decision, not endless coverage.

2. **Name the operator**
   Who runs, maintains, or consumes this — non-technical editor, maintainer, coding agent, buyer, user under time pressure — and at what level. Load the operator into the task framing itself. A technically correct answer that ignores who runs it is failed work. Recurring test: "Is this a good pattern for a nontechnical person?"

3. **Surface governing constraints and local conventions**
   What does the project already do? Generic answers underweight local convention; local reality decides over imported best practice. Prefer established paths when experiments start hardening into backbone.

4. **Name acceptance criteria and proof threshold**
   What would count as done? What evidence is enough (test, log, manual before/after, close read)? Prefer reversible probes when context is incomplete. Evidence is sufficient when a small strongest set has been directly read and the claim survives a weakening pass — then stop.

5. **Narrow until the next action is obvious and defensible**
   Once bounded: be fast, even impatient. Full certainty is not required. Further analysis past local boundedness is scope reopening — a failure mode, not rigor.

## Complexity Must Earn Its Place (At Frame Time)

Register complexity creep before anything else. Treat extra files, layers, branching, configurability, and defensive checks as suspect until they demonstrably improve usability, maintainability, or decision quality. Cutting questions:

- Can this config just be hardcoded values?
- Does this factory need an if-tree if the types already encode the behavior?
- Should local error handling stay if the library already covers it?
- Does this separation make the work easier to understand, change, and hand off — or harder?

Elegance, generality, future-proofing, exhaustive completeness, and polish are not virtues until they earn their place. They stay background until they cost legibility — then cut them.

**Earn every layer** is the standing architecture rule. "Best practice" is not sufficient justification.

## Evidence Sufficiency (Not Exhaustive Discovery)

Get enough direct context to avoid overreach — then stop and execute. Ungrounded fluency is a warning: output that sounds clean on thin evidence, broad matches, or a few-examples→big-claim jump should trigger tightening, not shipping. Bound every claim to what was actually inspected; say what remains unknown.

Speed is bought through reversibility and narrowed scope, never through relaxed correctness. Fast in reconnaissance and scoped probes; near structural commitment, correctness and maintainability outrank speed.

## Correct By Concretization, Not Adjectives

When something misses, do not say "make it better." Name the failure mode and replace the loose request with a tighter operating spec: what evidence to use, what to ignore, what shape the answer takes, what not to mention, proof threshold. He corrects by removing interpretive slack — "do it again under these constraints," not "try again." Convert corrections into standing constraints for the rest of the work.

## Mid-Task Change = Re-Baseline

When assumptions shift, stop optimizing the old plan. Restate as observable conditions, state transitions, gating rules, and fallbacks. Do not quietly adapt the obsolete frame.

## Delegation Bound

A collaborator can scout, summarize, rewrite, debug, or implement — but **scope, sequence, proof threshold, and output shape stay controlled**. Complete executable specs over partial strategic co-creation. Framing, proof standards, and final synthesis stay with him.

## Operationalization Bias

Across substantive work, prefer converting implicit expertise and scattered judgment into reusable operating machinery — explicit configs, structured records, simpler workflows, inspectable artifacts — not one-off chat answers. When energy drops, the recovery unit is a smaller inspectable artifact (checklist, simplified config, inventory), not more ideation.

## Neighbor Skills

- Thin atomic pre-contact only: `bound-before-solving`
- Discovery vs commitment speed / handoff rigor: `boundary-handoff`
- Collapse overbuilt surface: `complexity-reduction`
- Drift, blind patch, fluency without ground: `failure-recovery`
- Post-change proof: `verify-before-trust` / diagnosis path in failure-recovery

## Output Shape

1. **Mode** — explore / plan / execute (from prompt signals)
2. **Object** — what was inspected (paths/behaviors), observed vs inferred
3. **Operator** — who runs it, at what level
4. **Constraints** — local conventions, must-remain-true, exclusions
5. **Acceptance + proof threshold**
6. **Bounded next action** — obvious and defensible; or explicit "not enough contact yet → reversible probe X"
7. **Complexity budget** — layers allowed to earn place; default strip list if overbuilt

## Completion Criteria

- [ ] Real object contacted (or probe named) before prescription
- [ ] Operator named in the frame, not as an afterthought
- [ ] Prompt mode respected (no discovery theater on act-now; no build on pure explore)
- [ ] Acceptance criteria and proof threshold stated
- [ ] Stop condition clear — when framing ends and execution begins
- [ ] Claims bounded to inspected evidence; unknowns stated
- [ ] Complexity not pre-authorized by "best practice"
- [ ] Next action obvious without reopening settled scope

## Failure This Prevents

Polished, plausible work that never touched the real object, ignored who has to run it, or buried the decision under unearned structure — and the opposite failure: endless planning and discovery after the situation is already clear enough to act. Test: did framing force hidden complexity, assumptions, and scope into the open *before* effort compounded around them, and is the next action now obvious and defensible to the person who has to run it?
