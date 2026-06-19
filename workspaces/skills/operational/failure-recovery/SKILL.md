---
name: failure-recovery
description: Use when a response is drifting away from the work it claims to serve — recommending before inspecting, sounding fluent on thin evidence, accumulating structure without payoff, patching a bug without a diagnosis, or expanding search past the answerable core. Not needed for straightforward requests where the next move is already named and the evidence already supports it.
source_group: group-2
source_profile: operational
category: operational
compatibility: opencode
---

## When To Use

Load this when work is non-trivial and at risk of one of these specific drifts:
- you're about to recommend, implement, or answer before you've actually looked
- a clean-sounding draft is leaning on weak or absent source contact
- abstraction, helpers, config options, defensive checks, or file splits are piling up
- a fix is being made without a named cause
- search keeps gathering context after the core question is already answerable
- an output is technically correct but hard for the real operator to read, edit, or act on
- a prior analytical attempt missed on scope, rigor, or framing

## Do Not Use

Skip this when the asset, action, and output form are already named and the next move is obvious — extended analysis there reads as reopening settled scope. Skip it during early scouting, where rough and "good enough" is fine because you're only reducing uncertainty or finding candidates. The precision rules below bind tightly only when the output must guide implementation, sales, a non-technical user, or a later agent.

## First: Read The Stance

The right repair depends on what stage the work is in. Infer it from the user's own verbs and the shape of the task:
- plan-first verbs (look, decide, plan, explore, understand) → orientation or fit judgment; execution is premature
- act-now verbs (rewrite, add, search, note, make, treat this like) → execution wanted; another framework is premature
- the object is unclear → exploration: map project type, directory structure, build, tests, linting, style rules, existing instructions, or current workflow; surface constraints and name the operator before any recommendation
- multiple viable paths exist → planning: judge which path fits the real user, local conventions, complexity budget, and maintenance burden — then move quickly once an option clears those filters, don't keep deliberating
- observed behavior diverging from intended → diagnosis; separate actual vs expected before touching anything
- artifact exists but doesn't carry the point → refinement; tighten copy, cut moving parts, improve defaults, sharpen fit to the pain point
- the answer is already supported enough → stop; a bounded claim or next move does not require more exploration

Simplification is a standing override, not a stage. It can interrupt any of the above the moment the surface feels heavier than the job deserves.

Whatever the stage, task framing, proof standards, and final synthesis stay with the user. You can scout, retrieve, and execute — you don't get to move the standard.

## The Drifts And Their Repairs

**Getting ahead of the work.** Recommending before inspecting, implementing before understanding, or answering the exciting part before the first requested step. Repair: resequence. Do the requested first step first, look before you recommend, decide and plan before you build. The objection is to ungrounded speed, not to difficulty.

**Fluency without grounding.** A draft sounds clean but rests on weak evidence or a scope jump. Repair: narrow the brief, require direct passages and concrete files/logs/behavior, check the cases that would weaken the claim. If the support doesn't materialize, cut the claim — do not smooth it into something that sounds supported.

**Complexity outrunning understanding.** Layers accumulate without clear payoff. Repair: collapse the surface. Treat it like a config file — fewer files, direct defaults, explicit control points — until the control point is obvious and inspectable. If the implementation starts feeling harder to reason about than the problem itself, reopen the path choice; that's a valid reversal, not waste.

**Technically correct but not usable.** It works in code or prose but the real operator can't easily understand, edit, or act on it. Repair: evaluate against that actual user and simplify the path to them, not to an abstract ideal.

**Blind patch on a bug.** A fix not tied to a diagnosed cause. Repair: isolate the failure, name the cause, make the smallest change tied to that cause, verify the original failure is gone. A fix broader than its diagnosis stays untrusted — keep it scoped to what the diagnosis supports.

**Analytical miss on scope, rigor, or framing.** Repair is not "try again." It's "do it again under these stricter constraints" — explicit exclusions, proof thresholds, answer shape, things not to mention. Remove interpretive slack rather than re-explaining intent.

**Exploration that keeps expanding.** More context gathered after the answerable core is already visible. Repair: stop the broad search, use the strongest candidates, synthesize, and move on. Endless exploration is not rewarded once the evidence supports a bounded move.

## Truth-Contact Test

Before you let a claim stand, ask: have I had enough direct contact with the artifact to support exactly this move — and no more? Manually test behavior rather than trusting documentation or assumption. You don't need absolute certainty. You need enough contact to avoid speculative overreach, then stop. The trigger for intervention is fluency outrunning verification: a plausible explanation with no source contact, no cause diagnosis, or no before/after validation. When that happens, narrow scope and demand direct evidence rather than embellishing.

## What Restores Confidence

A repaired response feels grounded when the claim is bounded to what was actually inspected, the structure has visibly less surface than before, the fix maps to a named cause and the original failure is confirmed gone, and the next operator can use the output without reconstructing your reasoning. Stop there — adding more past that point reads as overprocessing.
