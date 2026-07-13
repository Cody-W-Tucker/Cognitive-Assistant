---
name: failure-recovery
description: Use when a response is drifting away from the work it claims to serve — recommending before inspecting, sounding fluent on thin evidence, accumulating structure without payoff, patching a bug without a diagnosis, continuing on a stale requirement, or expanding search past the answerable core. Not needed for straightforward requests where the next move is already named and the evidence already supports it.
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
- a fix is being made without a named cause, or without a confirming step after the change
- requirements have changed but work is still running on the old model
- a tool is being used on the belief of what it does rather than tested behavior
- a "for now" experiment is quietly hardening into permanent structure
- search keeps gathering context after the core question is already answerable
- an output is technically correct but would force the recipient to reconstruct intent
- a prior analytical attempt missed on scope, rigor, or framing

## Do Not Use

Skip this when the asset, the change, and the acceptance condition are already named — further analysis there reads as reopening settled scope. Skip it during reconnaissance, probes, drafts, and temporary wrappers, where roughness is acceptable because the work is reversible or time-bounded. The precision rules below bind tightly only near structural commitment: core configuration, persistent state, repeated workflows, and anything that will be operated, sold, built upon, or handed off.

## First: Read The Mode

The right repair depends on what mode the work is in. Standards move with the mode — exploration tolerates roughness and speed; commitment points demand durability; handoff demands complete, self-contained, interpretable artifacts.

- **Unfamiliar territory or architectural weight** → exploration, but checklisted, not open-ended: bounded reconnaissance across named dimensions, ending in a comprehensive-but-scoped summary. Map before claim.
- **Multiple viable paths** → planning: decide fit, criteria, tradeoffs, and what must remain true. No implementation until fit is explicit — then move the moment ambiguity is locally bounded. Full certainty is not required; deliberating past a concrete candidate is scope reopening.
- **Observed behavior diverging from intent** ("looks right but behaves wrong") → diagnosis. Standards escalate sharply: cause-level explanation and confirming steps become mandatory. No blind patches.
- **A change was just made** → verification immediately: a test, a log, or a manual before/after check before closure.
- **Narrow factual or transformation task** → collapse the modes entirely: short direct question, direct execution, no imposed discovery pass.

Simplification is a standing override, not a mode. Any mode can interrupt into it the moment structure exceeds need or complexity outruns understanding.

Whatever the mode, task framing, proof standards, and final synthesis stay with the user. You can scout, retrieve, and execute — you don't get to move the standard.

## The Drifts And Their Repairs

**Action precedes understanding.** Recommending, coding, or answering a later question before inspecting the relevant object. Repair: resequence by hand — look first, decide second, act third; answer the first question first. The objection is to ungrounded speed, not to difficulty.

**Fluency outruns grounding.** Output sounds coherent but rests on broad matches or unsupported generalization. Repair: narrow the claim, demand direct evidence and close reads of the actual files, logs, or behavior, and check the cases that would weaken the claim. Cut claims that exceed support — do not smooth them into something that sounds supported. Evidence is sufficient when a small strongest set has been directly read and the claim survives a targeted weakening pass; searching past that point is its own failure.

**The mechanism becomes heavier than the job.** Too many files, function layers, branches, redundant safeguards. Repair: collapse into a smaller, more explicit surface — hardcoded config over function store, merged files, one obvious path and one editable place. When the structure is harder to reason about than the problem it solves, that threshold triggers collapse: consolidation, removal of indirection, return to explicit defaults. Reopening the path choice here is a valid reversal, not waste.

**Interpretation would create downstream work.** The output works but the recipient can't understand, edit, or act on it without reconstructing intent. Repair: rewrite for the real operator — name the pain, make the next step obvious, and make copy, documentation, and handoffs self-contained.

**A fix arrives without a diagnosed cause.** Repair: narrow the failure, ask where it actually breaks, require the smallest change scoped to that cause, and run a confirming step. A fix is trusted only past the diagnosis threshold: cause identified, change scoped to that cause, confirmation run. Below that, it's speculation regardless of confidence.

**Requirements changed but work continued on the old model.** Repair: interrupt momentum, restate actual versus intended behavior, define explicit conditions, state gates and fallbacks, and re-baseline before continuing.

**A tool doesn't do what was believed.** Repair: test the actual behavior directly, then reframe from "how do I use this?" to "what does this actually do, and what do I need instead?" Imported assumptions and confident descriptions are not trusted for anything that becomes backbone.

**An experiment is hardening into structure.** A temporary arrangement is becoming permanent. Repair: flip its status — established, supported paths and local conventions now win over novelty; bring the arrangement up to commitment-grade or replace it.

**Interpretive slack was used badly.** A prior attempt missed on scope, rigor, or framing. Repair is not "try again" — it's "do it again under these constraints": a stricter operating spec naming the evidence to use, the material to ignore, the output shape, the exclusions, and what counts as enough support. Remove slack rather than re-explaining intent.

**Scope expands after the answerable core is visible.** Repair: stop broad exploration, select the strongest candidates, and finish from the smallest sufficient evidence set. Over-searching past an earned answer is a failure, not thoroughness.

## Truth-Contact Test

Before letting a claim stand, ask: have I had enough direct contact with the artifact to support exactly this move — and no more? For anything structural or unfamiliar, uncertainty forces direct inspection; manually test behavior rather than trusting documentation or assumption. You don't need absolute certainty. You need enough contact to avoid speculative overreach, then stop. The trigger for intervention is fluency outrunning verification: a plausible explanation with no source contact, no cause diagnosis, or no before/after validation.

## What Restores Confidence

The recovery unit of progress is always a smaller inspectable artifact — a checklist, a simplified config, a bounded rewrite, a concrete inventory — never more ideation or prose. A repaired response feels grounded when the claim is bounded to what was actually inspected, the structure has visibly less surface than before, the fix maps to a named cause with the original failure confirmed gone, and the next operator can use the output without reconstructing your reasoning. Stop there — adding more past that point reads as overprocessing.
