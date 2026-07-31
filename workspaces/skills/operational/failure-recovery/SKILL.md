---
name: failure-recovery
description: Use when a response is drifting away from the work it claims to serve — recommending before inspecting, sounding fluent on thin evidence, accumulating structure without payoff, patching a bug without a diagnosis, or expanding search past the answerable core. Not needed for straightforward requests where the next move is already named and the evidence already supports it.
source_group: group-2
source_profile: operational
category: operational
compatibility: opencode
---

# Failure Recovery

## When To Use

Load this when work is non-trivial and at risk of one of these drifts:

- About to recommend, implement, or answer before you have actually looked
- Clean-sounding draft leaning on weak or absent source contact
- Abstraction, helpers, config options, defensive checks, or file splits piling up
- A fix being made without a named cause
- Search still gathering context after the core question is already answerable
- Output technically correct but hard for the real operator to read, edit, or act on
- Prior analytical attempt missed on scope, rigor, or framing
- Requirements changed but work continued on the old model
- Tool or system not doing what was believed

## Do Not Use

- Asset, action, and output form already named and next move obvious — extended analysis reopens settled scope
- Early scouting where rough and "good enough" is fine because you are only reducing uncertainty
- Precision rules below bind tightly only when output must guide implementation, sales, a non-technical user, or a later agent
- Pure initial bounding with no drift yet — `scope-framing`
- Pure discovery/commitment line call with no repair needed — `boundary-handoff`
- Pure structural excess with clear job — may interrupt into `complexity-reduction` after stance is read

## First: Read The Stance

The right repair depends on stage. Infer from the user's verbs and task shape:

| Signal | Stance | Premature move |
| --- | --- | --- |
| look, decide, plan, explore, understand | orientation / fit | execution |
| rewrite, add, search, note, make, treat this like… | execution | another framework |
| object unclear | exploration — map type, dirs, build, tests, lint, style, rules, workflow; name operator before recommending | prescription |
| multiple viable paths | planning — fit to real user, local conventions, complexity budget, maintenance; move once an option clears filters | endless deliberation |
| observed ≠ intended | diagnosis — separate actual vs expected before touching anything | blind patch |
| artifact exists but doesn't carry the point | refinement — tighten copy, cut moving parts, sharpen pain-point fit | new architecture |
| answer already supported enough | stop | more exploration |

**Simplification is a standing override, not a stage.** Interrupt any stance the moment the surface is heavier than the job — route collapse mechanics to `complexity-reduction` while keeping diagnosis ownership here.

Whatever the stage: **task framing, proof standards, and final synthesis stay with the user.** You can scout, retrieve, and execute — you don't get to move the standard.

## Recovery Sequence

1. **Name the drift** (one of the types below)
2. **Name stance** (table above)
3. **Resequence or constrain** — apply the matching repair
4. **Truth-contact check** — enough direct contact for exactly this move, no more
5. **Emit repaired artifact or next step** — smaller inspectable unit preferred
6. **Verify if a change was made** — claim → check → result → remaining unverified surface

## The Drifts And Their Repairs

**Getting ahead of the work.** Recommending before inspecting, implementing before understanding, answering the exciting part before the first requested step.  
→ **Resequence.** Requested first step first; look → decide → act. Objection is to ungrounded speed, not to difficulty. Respect sequence visibly; never let the interesting part jump the queue.

**Fluency without grounding.** Draft sounds clean but rests on weak evidence or a scope jump.  
→ **Narrow the brief.** Require direct passages and concrete files/logs/behavior; check cases that would weaken the claim. If support does not materialize, **cut the claim** — do not smooth it into something that sounds supported. Small strongest set of close reads > broad weak matches.

**Complexity outrunning understanding.** Layers accumulate without clear payoff.  
→ **Collapse the surface** (use complexity-reduction mechanics). Config-file energy: fewer files, direct defaults, explicit control points until the control point is obvious. If implementation is harder to reason about than the problem, reopen the path choice — valid reversal, not waste.

**Technically correct but not usable.** Works in code or prose; real operator cannot easily understand, edit, or act.  
→ **Evaluate against that actual user** and simplify the path to them, not to an abstract ideal. "Is this a good pattern for a nontechnical person?"

**Blind patch on a bug.** Fix not tied to a diagnosed cause.  
→ **Isolate → name cause → smallest change tied to cause → verify original failure gone.** A fix broader than its diagnosis stays untrusted. No "it should work now." Ship cause + minimal change + before/after together. Thin siblings: `diagnose-before-patching`, then `verify-before-trust`.

**Analytical miss on scope, rigor, or framing.**  
→ Not "try again." **Do it again under stricter constraints:** explicit exclusions, proof thresholds, answer shape, things not to mention. Remove interpretive slack. Convert the miss into standing acceptance criteria for the rest of the work.

**Exploration that keeps expanding.** More context after the answerable core is visible.  
→ **Stop** broad search; use strongest candidates; synthesize; move on. Endless exploration is not rewarded once evidence supports a bounded move.

**Requirements changed; old plan continues.**  
→ **Interrupt momentum.** Restate actual vs intended; define conditions, state gates, fallbacks; re-baseline. Do not optimize the obsolete model.

**Tool doesn't do what was believed.**  
→ **Test actual behavior**, then reframe from "how do I use this?" to "what does this actually do, and what do I need instead?"

## Diagnosis Detail (When Observed ≠ Intended)

Standards escalate sharply:

1. State observed failure and expected behavior in concrete terms
2. Reproduce or localize before changing anything when feasible
3. Trace symptom → cause with smallest useful evidence (logs, tests, diffs, inputs, config, runtime)
4. Prefer state/precondition cases: what a new user sees first; what appears only after status exists; what fallback shows when real data is absent — happy-path-only fixes don't clear the bar
5. Change only what the cause explains
6. If cause uncertain, label patch provisional and keep the next check narrow
7. Verify immediately after change before closure

## Truth-Contact Test

Before letting a claim stand: have I had enough direct contact with the artifact to support exactly this move — and no more? Manually test behavior rather than trusting documentation or assumption. Absolute certainty not required; enough contact to avoid speculative overreach, then stop.

**Intervention trigger:** fluency outrunning verification — plausible explanation with no source contact, no cause diagnosis, or no before/after validation. Response: narrow scope and demand direct evidence rather than embellish.

## What Restores Confidence

A repaired response feels grounded when:

- Claim is bounded to what was actually inspected
- Structure has visibly less surface than before (if complexity was the drift)
- Fix maps to a named cause and original failure is confirmed gone
- Next operator can use the output without reconstructing your reasoning

**Stop there.** Adding more past that point reads as overprocessing.

Recovery unit of progress is always a **smaller inspectable artifact** — checklist, simplified config, bounded rewrite, concrete inventory, restated claim — not more ideation or prose.

## Neighbor Skills

- Diagnose only: `diagnose-before-patching`
- Verify only: `verify-before-trust`
- Pre-frame before drift: `scope-framing`
- Line-crossing rigor: `boundary-handoff`
- Collapse mechanics: `complexity-reduction`
- Atomic bound: `bound-before-solving`

## Output Shape

1. **Drift named**
2. **Stance** (orientation / fit / execution / diagnosis / refinement / stop)
3. **Repair applied** (resequence / narrow / collapse / retarget operator / diagnose+verify / stricter spec / stop search / re-baseline / retest tool)
4. **Evidence** — what was contacted; observed vs inferred
5. **Corrected claim or artifact**
6. **If changed:** cause → minimal change → verification result → remaining unverified surface
7. **Standing constraint** extracted from the miss (if any) for subsequent work

## Completion Criteria

- [ ] Drift and stance named before repairing
- [ ] Matching repair applied (not generic "try harder")
- [ ] No blind patch: cause named or patch labeled provisional with narrow check
- [ ] Claims cut when support fails — not smoothed
- [ ] Sequence respected (first requested step first)
- [ ] Verification run when behavior changed; result reported without laundering uncertainty
- [ ] Operator usability checked when "works but unusable" was the drift
- [ ] Stopped when answer earned — no exploratory sprawl past sufficiency
- [ ] Framing/proof/synthesis authority left with the user

## Failure This Prevents

Continuing fluent motion in the wrong direction: ungrounded recommendations, confident patches without diagnosis, complexity theater, endless search after the answer is earned, and polished misses that never become stricter specs. Restores the operational control loop: inspect while unclear, execute when bounded, diagnose on divergence, verify before declaring success, compress when heavy.
