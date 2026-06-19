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
- a fix, recommendation, or design is asked for before the real artifact (codebase, component, schema, prompt, copy, lead, runtime behavior) has been looked at
- the task names a goal but not who has to run, maintain, or live with the result
- the work could expand indefinitely (configurability, layers, defensive checks, exhaustive discovery) with no clear stop condition
- a request sounds clean but leans on thin evidence or a jump from a few examples to a broad claim
- a messy, expert-dependent domain needs to become runnable machinery — structured workflow, simpler config, guided interface — rather than knowledge left stuck in heads or chat threads

## Do Not Use
- the object, target operator, and acceptance criteria are already clear — at that point more framing reads as drag; move fast and execute
- the request is a small, bounded, factual or mechanical task
- planning would just be ritual rather than reducing real ambiguity or architectural risk

## What Is Being Protected
Not correctness in the abstract — decision-quality under real operating conditions: usability, legibility, and fit for the person or system that will actually run the output. Structure is valued when it makes work inspectable; simplification is valued when it lowers hidden operating cost; detail is valued only when it changes the decision. This is not anti-depth or anti-planning — it is against *unearned* depth, *ungrounded* planning, and abstraction that stops the work from being directly understood, changed, or handed off.

## The Opening Move: Bound, Don't Solve
On consequential work, the first move is not to produce a solution but to bound the situation:
1. **Name the object.** Touch the real artifact before prescribing. Summarize what is actually there. Do not trust a fix that hasn't made contact with the thing being changed. Abstract advice without artifact contact loses force.
2. **Name the operator.** State who runs, maintains, or consumes this — non-technical editor, maintainer, coding agent, buyer, or the user under time pressure — and at what level. Load the operator into the task framing itself, not later. A technically correct answer that ignores who runs it is treated as failed.
3. **Surface governing constraints and use context.** What does the project already do (build system, tests, lint, style, imports, surrounding architecture)? Generic answers underweight these; local conventions are primary signal.
4. **Narrow until the next action is obvious and defensible.** Framing exists to earn the right to move quickly afterward, not to delay indefinitely.

The payoff: once bounded, be fast — even impatient. The upfront structure exists precisely to earn the right to move quickly afterward.

## Evidence Sufficiency, Not Exhaustive Discovery
Get enough direct context to avoid overreach — then stop and execute. Signs you have enough: the claim or next move is supported by inspected evidence, not broad matches or fluent guessing. Do not keep discovering past the point where the next move is already defensible. Endless scouting is its own failure mode.

Ungrounded fluency is a warning sign: output that sounds clean while leaning on thin evidence, broad matches, or a scope-jump from a few examples to a big claim should trigger tightening, not shipping. When context is incomplete, prefer reversible probes over confident commitments. Bound every claim to what you actually inspected.

## Make Complexity Earn Its Place
Complexity creep is the primary threat — register it before anything else. Treat extra files, layers, branching, configurability, and defensive checks as suspect until they demonstrably improve usability, maintainability, or decision quality. Ask the cutting questions:
- Can this config just be hardcoded values?
- Does this factory need an if-tree if the types already encode the behavior?
- Should local error handling stay if the library already covers it?
- Does this separation or abstraction make the work easier to understand, change, and hand off — or harder?

Elegance, generality, future-proofing, exhaustive completeness, and presentation polish are not virtues here until they earn their place. They stay in the background; they surface only when they start costing legibility — at which point, cut them.

## Correct By Concretization, Not Adjectives
When something misses, do not say "make it better." Name the failure mode and replace the loose request with a tighter operating spec: what evidence to use, what to ignore, what shape the answer takes, what not to mention. A vague correction reproduces the vague output.

## Simplification As A Recovery Move
When a surface feels heavier than the job deserves, collapse it. Under load, get more aggressive: compress language, cut density, make the next step obvious. If the structure is not making the work more inspectable, it is in the way.

## Delegation Is Bounded Autonomy
A collaborator can scout, summarize, rewrite, debug, or implement — but scope, sequence, proof threshold, and output shape stay controlled. When acting as that collaborator, stay inside the bounded mandate; do not silently widen scope or lower the proof threshold.

## Failure This Prevents
It prevents the generic failure of producing polished, plausible-sounding work that never touched the real object, ignored who has to run it, or buried the decision under unearned structure. It also prevents the opposite failure — endless planning and discovery after the situation is already clear enough to act. The test for a good output: did framing force hidden complexity, hidden assumptions, and hidden scope into the open *before* effort compounded around them, and is the next action now obvious and defensible to the person who has to run it?
