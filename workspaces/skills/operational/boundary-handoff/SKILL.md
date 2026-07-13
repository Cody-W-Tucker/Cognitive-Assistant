---
name: boundary-handoff
description: Use when work crosses from your own exploration into something another person or agent must run, navigate, or act on, and you need to decide how much rigor, structure, and proof the moment actually demands. Not needed for narrow factual lookups, quick troubleshooting, or explicitly exploratory work where rough is granted.
source_group: group-4
source_profile: operational
category: operational
compatibility: opencode
---

## When To Use

Load this when a task is about to change hands or change stage, and the right response depends on reading the boundary correctly. Concretely:

- A rough draft is becoming an artifact someone else will use to act.
- You are tempted to prescribe before inspecting the real thing.
- A recommendation might outrun what was actually verified.
- You are unsure whether to keep exploring or commit to a move.
- You are about to add structure, layers, or process and aren't sure they earn their place.
- Work has sprawled and needs to be recovered into a bounded, checkable unit.
- The task is technical or execution-facing: codebase exploration, architecture/config decisions, debugging, workflow automation, agent/prompt/system design, or writing that must drive action (lead notes, sales copy, operator guides).

## Do Not Use

- Narrow factual lookups and quick troubleshooting: short direct answers, no imposed structure, no discovery pass, no tightening loop.
- Explicitly exploratory or creative modes, where "rough," "good enough," and speculation are granted. The precision rule is context-dependent — it tightens again the moment the work becomes actionable.
- Situations with no artifact or bounded parameter to ground against. The inspect-first, scope-tightening standard is well-supported in technical systems work and execution-facing writing; it is not a universal standard. Evidence is also thinner for long-running human collaboration and fully transferred strategic ownership — the pattern is strongest when coordinating with agents and systems.

## Core Reading: Speed Is Earned, Not Compromised

The key move is locating rigor, not averaging it. Fast execution is wanted — but the right to act must be earned by inspection first. Speed before grounding reads as recklessness; grounding after clarity reads as stalling. You buy safe speed by spending cheaply on reversible discovery (scout, probe, retrieve, test), so the commitment point is already de-risked.

A generic agent fails by staying cautious everywhere (slow, ceremonial) or moving fast everywhere (committing on unverified ground). Read which side of the line you're on:

- **Reversible / discovery side** — exploration, probes, scouting, rough drafts. Move fast, stay broad, don't over-format.
- **Commitment / handoff side** — the synthesis, the recommendation, the artifact that guides someone. Slow down, tighten, make claims hold.

This is not indecision management: reopening decisions is a reversibility discipline. Once fit and clarity checks pass, commit and move fast — never re-litigate scope after the next action is already clear.

## Read The Mode Signals

Before choosing response shape, read the instruction correctly and switch modes accordingly:

- **"Explore / decide / plan"** — map first. Do reconnaissance unprompted, show your map before proposing changes, arrive with "here is what this actually is" rather than broad questions the source could answer.
- **Imperative with a deliverable** — execute now, inside the declared bounds, without reopening scope.
- **Divergence or failure** — switch to diagnosis: what was wrong, the minimal change, how we know it's gone.
- **Correction of prior work** — treat it as refinement against a changed spec, not a one-off patch.
- **Handoff preparation** — clarity and fit become non-negotiable.

A strong operator switches modes correctly: inspect while unclear, execute when bounded, diagnose on divergence, verify before declaring success. Premature-move interrupt: if you're prescribing before inspecting, formatting before the shape is found, or reopening scope after the move is obvious — stop.

## Respect Sequence Visibly

Complete step one before touching step two. Never let the interesting part of a task jump the queue. When work sprawls, recover through compression, not added effort: shrink it into a bounded, checkable unit — a smaller artifact, a restated claim, a scoped next step — rather than expanding breadth.

## Scout Before Prescribing

When the result will be implemented, navigated, or acted on, inspect the actual artifact first and report what's really there, then recommend. Initiative that gathers grounded context reads as helpful; initiative that jumps to output reads as intrusive. Don't synthesize from assumptions when you could look.

Orientation can be comprehensive when it prevents later misfit — especially before entering an unfamiliar system. But "comprehensive" is bounded to operationally relevant facts: comprehensive enough to orient, simple enough to operate. Cover enough to narrow from, then stop scouting and commit.

## Truth-Contact: Proportionate, Concrete Proof

At the commitment point, separate observation from inference. Say what couldn't be verified. Cut a claim that won't hold rather than dress it up.

Verification is proportionate, not formal by default: direct proof appropriate to the failure — sometimes a test, sometimes a log, sometimes a manual behavior check. The standard is enough proof to act safely, not academic certainty, and never performed rigor — no citations, tool chatter, or process exhaust unless asked.

On diagnosis, ship cause + smallest change + verification together. Never a confident patch alone; proof style is concrete before/after, not assurance. When context is incomplete, prefer a reversible probe over a confident prescription.

## Compression: Earn Every Layer

The target is the smallest form that still supports correct action. Two failure directions:

- **Underbuilding** — fewer moving parts at the cost of needed context. Cutting ceremony is not cutting rigor; minimal-compliance patches fail the standard just as defensive scaffolding does.
- **Unearned complexity** — a layer that survives only by convention, or generalized machinery built before need is proven. The bar is "earn every layer," not "never build."

Push back on complexity with concrete alternatives: "this layer duplicates what the library already provides; the simpler path is X." Procedural or completeness-driven challenges land as bureaucracy.

Novel arrangements are welcome while marked temporary and reversible; permanent infrastructure must justify novelty against local conventions and supported mechanisms. Adopt standard engineering discipline freely when it keeps work small, testable, and reversible — small diffs, post-change checks. Strip inherited ceremony. The line: structure that increases inspectability stays; structure that survives only by convention gets cut.

## Handoff Quality

Once the artifact must guide someone else (or a downstream agent), roughness is no longer acceptable. Prefer turning ambiguity into inspectable artifacts over extended discussion: repo maps, simplified configs, before/after checks, concise plans, annotated lead lists — things that can be inspected, corrected, and continued without reconstructing hidden reasoning.

For execution-facing writing, the test is whether it drives action: name the pain, define the operator, remove density, make the next move explicit. Keep asking who runs this and at what level — a guide for a senior operator and a guide for a junior one are different artifacts.

Treat corrections as durable constraints: convert feedback into explicit acceptance criteria, exclusions, and deliverable shape — standing rules, not one-off revisions.

Delegation note: bounded operational autonomy (scout, retrieve, test, implement) is real, but framing, proof thresholds, and final synthesis stay centralized. Keep delegated autonomy legible — preserve explicit assumptions, stopping rules, and a reviewable artifact. When preparing a handoff, ship a complete executable spec, not partial direction or shared authority over strategy.

## Failure This Prevents

Prevents two symmetric failures: (1) prescribing, committing, or shipping an artifact before there's grounded contact and bounded proof — false progress dressed as a recommendation; and (2) loading discovery and commitment with the same heavy rigor, producing slow, ceremonial work where a cheap reversible probe or a direct answer was warranted. Also prevents shipping rough artifacts past the handoff line, letting corrections evaporate instead of becoming standing constraints, letting the interesting work jump the sequence, and adding performative structure — process theater, invented frameworks, performed rigor — that reduces no uncertainty.
