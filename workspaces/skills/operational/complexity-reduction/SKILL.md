---
name: complexity-reduction
description: Use when work is directionally right but at risk of being unverifiable, hard to operate, or heavier than the job warrants — when output could look complete while leaving the next operator to reconstruct hidden structure. Not needed for straightforward factual, formatting, or procedural requests where proof and operability are already obvious.
source_group: group-3
source_profile: operational
category: operational
compatibility: opencode
---

# Complexity Reduction

## When To Use

Load this when any of these are in play:

- About to summarize, simplify, redesign, or hand off something that could sound informed while drifting from actual files, behavior, or operator
- A simplification is on the table and you cannot yet tell whether it removes real complexity or just renames it
- Output risks becoming structurally heavier than the task (extra layers, dependencies, branching, frameworks, citations, tool chatter, multi-voice prose)
- Tempted to claim "it should work" without a concrete before/after/confirm path
- Deliverable will be operated by someone specific — non-technical editor, coding agent, buyer who needs the point immediately
- User signal: "this seems overly complex," too many files, factory/if-tree smell, defensive scaffolding already covered by a library
- Structure has become harder to reason about than the problem it solves

## Do Not Use

- Plain factual answers, small edits, or mechanical procedures where verification and usability are not in question
- Cases where adding structure is the actual job and already proven necessary
- Scope still unbound (no object/operator/acceptance) — `scope-framing` first
- Pure discovery-vs-commitment pacing / handoff polish — `boundary-handoff`
- Blind patch or fluency-without-ground drift mid-repair — `failure-recovery` (may interrupt *into* this skill after diagnosis)

## What This Owns

**Structural simplification with truth-contact and operator fit** — collapse unearned machinery while preserving the function that matters and leaving the next decision guesswork-free.

Does **not** own: initial bounding, mode routing, relational motive, or full diagnosis loops.

Standing rule from profile: **earn every layer**. Best practice is not justification. Cutting ceremony is not cutting rigor.

## Two-Halves Test (Before Calling Work Done)

Strong work requires both halves; one without the other is unfinished:

1. **Simplify** to the minimum form that preserves real utility. Remove unnecessary moving parts, but keep every piece of information needed to act safely — fit the operator who maintains or runs it.
2. **Then add enough concrete structure** that the next decision needs no guesswork. Detail in the dimension that makes the main path obvious — not detail elsewhere that hides the main path.

Only half one → shallow. Only half two → overprocessed. Detail alone never qualifies — the test is whether the result is **decision-ready**.

Comprehensiveness and simplification are demanded together at different levels: mechanism no more complex than necessary; act-relevant context has no obvious holes.

## Collapse Sequence

1. **Name the job**
   What must this structure actually perform for which operator? One sentence. If the job is unclear, stop collapsing and frame first.

2. **Inventory moving parts**
   Files, layers, indirection, config surfaces, branches, defensive checks, frameworks, prose voices. Touch the real artifact — refuse to judge a pattern in the abstract.

3. **Score each part: load-bearing vs decorative/defensive**
   What does it buy — clarity, safety, operator ease, reversibility — vs convention, future-proofing cosplay, or sophistication display?

4. **Apply real-simplification tests**
   - Did the number of places intent lives go *down*? One obvious editable surface counts. Spreading across new indirection does not.
   - Would the actual operator find it easier to run, edit, rerun, or verify — or just differently arranged?
   - Did you import generic architecture when a simpler local convention exists? Back it out.
   - Can config be hardcoded values instead of a function store?
   - Can types replace an if-tree in a factory?
   - Does local error handling duplicate what the library already covers?
   - Should separate files merge?

5. **Collapse**
   Merge, hardcode, delete, defer. Prefer: hardcoded config over function store; merged files; one obvious path; explicit defaults; smaller inspectable artifact.

6. **Re-check two-halves + proof path**
   Main path obvious? Operator can act without reconstructing hidden structure? Claims still tied to inspected evidence? Before/after/confirm path exists if behavior changed?

## Real-Simplification vs Renaming

Before claiming you cut complexity:

| Signal | Real cut | Rename / shuffle |
| --- | --- | --- |
| Intent locations | Fewer | Same or more behind new names |
| Operator path | Shorter, clearer | Different ceremony, same burden |
| Verification | Easier to see if it works | Harder; trust required |
| Local convention | Respected or intentionally replaced with simpler | Imported generic architecture |

If an abstraction cannot be explained through the real files, fields, behavior, or workflow, it loses credibility. Direct contact often changes the next move — let it.

## Anti-Performativity Interrupts

Treat as failure signals and strip:

- Citations, tool references, meta-context, invented frameworks
- Flowery or multi-voice output that exposes the generation process
- Elaborate, plausible-sounding output that is hard to verify or operate
- Detail in the wrong dimension that makes the main path harder to see
- Ceremony for convention's sake; defensive scaffolding that duplicates the stack

Sophistication that hides unverifiability is weak work. Prefer compact, concrete, evidence-bounded prose.

Unsupported confidence is lower quality than a narrower, qualified answer.

## Proof-Path Requirement

Replace "it should work" with: **this was wrong → this changed → this confirms the failure is gone** (or: this was heavy → this collapsed → operator can now do X without Y).

Pair cause-level diagnosis with bounded verification when behavior changes: small change, confirmed against original failure. When behavior is opaque, manufacture an inspectable surface (e.g. broken command → emits a usable log) rather than reasoning in the dark.

Cutting ceremony ≠ accepting unproven patches. Durable, cause-diagnosed fixes still required.

## Handoff Check

Before finishing, confirm the artifact is decision-ready:

- Someone can judge, implement, revise, or hand off without inferring missing structure
- Criteria, tradeoffs, and limits used are visible — that visibility earns trust
- Compresses future work: easier to rerun, hand off, edit, or verify later
- Survives contact with the *actual* operator (non-technical editor, coding agent, buyer)

Artifacts are coordination objects: repo summary, scoped plan, config, lead list, rewritten message — next person works without reinventing the task.

## Recovery Under Load

When energy, drift, or overload hits: shrink to a bounded unit with a visible completion test — simpler config, checklist, one concrete decision, bounded rewrite — not more ideation or breadth. Smaller inspectable artifacts restore momentum.

Any mode can interrupt into this skill the moment the surface feels heavier than the job deserves. Under load, get more aggressive: compress language, cut density, make the next step obvious.

## Experiment Hardening

Novel arrangements are welcome while marked temporary and reversible ("for now" / "later"). When a temporary arrangement starts hardening into permanent structure, collapse novelty toward established, supported paths and local conventions unless novelty still earns its keep on the real operator.

## Neighbor Skills

- Atomic collapse only (thin): `collapse-unearned-complexity`
- Pre-bound scope: `scope-framing`
- Discovery vs commitment / handoff rigor: `boundary-handoff`
- Drift, blind patch, expanding search: `failure-recovery`
- Packaging for a decision-maker: `decision-ready-not-impressive`

## Output Shape

1. **Job + operator** (one line each)
2. **Inventory** — moving parts and what each claims to buy
3. **Cut list** — remove / merge / hardcode / defer (with why)
4. **Keep list** — load-bearing remainder
5. **Lean form** — the simplified surface (config shape, file layout, prose path)
6. **Two-halves verdict** — utility preserved? next decision guesswork-free?
7. **Proof path** — how we know it is simpler *and* still correct/operable

## Completion Criteria

- [ ] Job and operator named before collapsing
- [ ] Real artifact contacted; not abstract pattern judgment
- [ ] Real-simplification tests passed (not rename shuffle)
- [ ] Both halves of two-halves test hold
- [ ] Anti-performative residue stripped
- [ ] Proof path present if behavior or operability claim changed
- [ ] Actual operator could run/edit/verify without reconstructing hidden structure
- [ ] No imported generic architecture that lost to a simpler local convention

## Failure This Prevents

False progress: output that looks complete but cannot be verified, cannot be operated by the intended person, or hides added maintenance cost behind fluent language. Weak execution is fluent but ungrounded — sounds informed while drifting from evidence. Sharpest failure signal: the user must manually restate scope, evidence rules, exclusions, or output shape after receiving the work. If you can foresee that restatement, fix it before delivering.

Also prevents: shallow minimalism that strips needed act-context; overprocessed configurability that must be serviced instead of finishing the job.
