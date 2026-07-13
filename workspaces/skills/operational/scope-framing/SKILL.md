---
name: scope-framing
description: Use when a task carries design, implementation, or judgment weight and the obvious move is to start solving before the object, operator, and acceptance criteria are pinned down. Not needed for straightforward factual, formatting, or well-bounded procedural requests.
source_group: group-1
source_profile: operational
category: operational
compatibility: opencode
---

## When To Use
Load this when the request could be answered immediately but answering early would commit effort around hidden scope, hidden assumptions, or an unnamed operator. Typical triggers:
- a fix, recommendation, or design is asked for before the real artifact (codebase, component, schema, prompt, copy, lead data, logs, runtime behavior) has been looked at
- the task names a goal but not who has to run, maintain, or live with the result
- the work could expand indefinitely (configurability, layers, defensive checks, exhaustive discovery) with no clear stop condition
- a request sounds clean but leans on thin evidence or a jump from a few examples to a broad claim
- assumptions have shifted mid-task and the old plan is being patched instead of re-based
- a messy, expert-dependent domain needs to become runnable machinery — structured workflow, simpler config, guided interface — rather than knowledge left stuck in heads or chat threads

## Do Not Use
- the object, target operator, and acceptance criteria are already clear — at that point more framing reads as drag; move fast and execute
- the prompt itself signals execution mode: imperative verbs with the deliverable embedded ("rewrite this to make more sense," "add these as leads, note the pain point") already collapse acceptance criteria into the request — do the work
- the request is a small, bounded, factual or mechanical task
- planning would just be ritual rather than reducing real ambiguity or architectural risk

## What Is Being Protected
Not correctness in the abstract — decision-quality under real operating conditions: usability, legibility, and fit for the person or system that will actually run the output. This guards against two failure modes at once: acting on a false model of the system (fluent answers built on thin grounding), and carrying complexity that outruns understanding (clever structure that is expensive to operate and hard to trust, hand off, or revise). Both halves are the same control mechanism pointed in different directions: structure is added when ambiguity is high; structure is stripped when it stops earning its keep. The constant is legibility — work must stay understandable enough to be judged directly by whoever operates it.

## Read The Mode Before Anything Else
Prompts encode mode. "Explore / decide / plan / understand" signals planning-first: bound the situation before producing. Imperative verbs with embedded deliverables signal execution-now: the framing work is already done. Misreading mode in either direction — solving when asked to scope, or scoping when asked to execute — is a sequencing failure, and ordering violations create friction more reliably than errors do. Inspect before prescribe. Answer the first question before the second. Orient before expanding.

## The Opening Move: Bound, Don't Solve
On consequential work, the first move is not to produce a solution but to bound the situation:
1. **Name the object.** Touch the real artifact before prescribing — project type, directory structure, build system, testing, linting, style, existing rules, current copy, actual data. Summarize what is actually there. Recommendations must be earned by contact with the real system; abstract advice without artifact contact loses force.
2. **Name the operator.** State who runs, maintains, or consumes this — nontechnical editor, maintainer, coding agent, buyer — and at what level. "Is this a good pattern for a nontechnical person?" is a first-class quality filter, not a nicety. A technically correct answer that ignores who runs it is treated as failed.
3. **Surface governing constraints and use context.** What does the project already do? Local conventions are primary signal; generic completeness is noise unless bounded to act-relevant facts — build, test, lint, style, rules, the pain point, the constraint that determines the decision.
4. **Narrow until the next action is obvious and defensible.** Framing exists to earn the right to move quickly afterward, not to delay indefinitely.

The payoff: once ambiguity is locally bounded and the next move is obvious, further analysis reads as friction. Execute directly.

## Evidence Sufficiency, Not Exhaustive Discovery
Get enough direct context to avoid overreach — then stop and execute. A small set of closely inspected examples outweighs broad weak matches or smooth generalization. Fluent output on thin contact is risk, not progress: if the answer sounds clean while leaning on broad matches or a scope-jump from a few examples to a big claim, tighten instead of shipping. When context is incomplete, prefer reversible probes over confident commitments — speed is bought through reversibility and narrowed scope, never through relaxed correctness. Bound every claim to what was actually inspected. Near structural commitment, correctness and maintainability outrank speed.

## Make Complexity Earn Its Place
Complexity creep is the primary threat — register it before anything else. "This seems overly complex" should fire early. The issue is not part-count alone but whether behavior is hidden across layers, hard to verify, or disproportionate to the immediate job. Treat extra files, config factories, layered orchestration, and defensive checks as execution defects until they demonstrably buy clarity. "Best practice" is not sufficient justification. Ask the cutting questions:
- Can this config just be hardcoded values?
- Does this factory need an if-tree if the types already encode the behavior?
- Should local error handling stay if the library already covers it?
- Does this separation make the work easier to understand, change, and hand off — or harder?

Elegance, generality, future-proofing, and polish stay in the background; polish becomes operational only when wording obscures action or the artifact must communicate or hand off.

## Fixes Require Cause, Smallest Change, Proof
"It should work now" earns nothing. The loop is: isolate the failure, explain the cause, change narrowly, verify against the original failure with concrete before/after behavior. In debugging, state and precondition cases become signal fast — what a new user sees first, what appears only after status exists, what fallback shows only when real data is absent. Happy-path fixes don't clear the bar.

## Mid-Task Change Triggers Re-Baselining
When assumptions shift, stop optimizing the old plan. Restate the work as observable conditions, state transitions, gating rules, and fallbacks — a fresh bound on the changed situation, not an adaptation of a plan whose premises no longer hold.

## Correct By Concretization, Not Adjectives
When something misses, do not say "make it better." Rewrite the job with explicit boundaries: what evidence to use, what to exclude, the required shape, the proof threshold. Remove interpretive slack rather than negotiating or granting another free pass. A vague correction reproduces the vague output.

## Compression As The Recovery Move
Under drift or overload, do not push through with breadth. Shrink the problem to a bounded unit with a visible completion test — a simpler config, a checklist, one concrete decision. If the structure is not making the work more inspectable, it is in the way; collapse it.

## Delegation Is Bounded Autonomy
A collaborator can scout, summarize, rewrite, debug, or implement — but scope, sequence, proof threshold, and output shape stay controlled. When acting as that collaborator, stay inside the bounded mandate; do not silently widen scope or lower the proof threshold.

## Failure This Prevents
It prevents polished, plausible-sounding work that never touched the real object, ignored who has to run it, or buried the decision under unearned structure. It also prevents the opposite failure — endless planning and discovery after the situation is already clear enough to act. The test for a good output: did framing force hidden complexity, hidden assumptions, and hidden scope into the open *before* effort compounded around them — and is the result legible enough that the actual operator can judge it directly?
