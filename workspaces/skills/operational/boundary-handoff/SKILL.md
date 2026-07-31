---
name: boundary-handoff
description: Use when work crosses from your own exploration into something another person or agent must run, navigate, or act on, and you need to decide how much rigor, structure, and proof the moment actually demands. Not needed for simple lookups, quick troubleshooting, or one-off how-to answers where direct response is fine.
source_group: group-4
source_profile: operational
category: operational
compatibility: opencode
---

# Boundary Handoff

## When To Use

Load this when a task is about to change hands or change stage, and the right response depends on reading the boundary correctly:

- A rough draft is becoming an artifact someone else will use to act
- You are tempted to prescribe before inspecting the real thing
- A recommendation might outrun what was actually verified
- You are unsure whether to keep exploring or commit to a move
- You are about to add structure, layers, or process and aren't sure they earn their place
- Technical, revision-heavy, or execution-facing work: codebase exploration, architecture/config, debugging, design review, prompt/system work, agent workflows, lead enrichment, sales rewriting
- Preparing a spec or deliverable for a downstream agent or non-technical operator

## Do Not Use

- Simple factual lookups, quick troubleshooting, one-off how-to: answer directly — no decomposition, no imposed format, no tightening loop
- Open-ended philosophical or phenomenological exploration: approximation permitted; don't force operational artifact standards without a physical artifact or bounded business parameter
- Initial scope still unnamed (object/operator/acceptance missing) — use `scope-framing` first
- Mechanism is simply overbuilt and needs collapse — `complexity-reduction`
- Response is drifting mid-work (blind patch, fluency without ground) — `failure-recovery`

## Core Reading: Speed Is Bought, Not Compromised

Locate rigor; do not average it. Speed and rigor resolve by **which side of the line** you are on, not by compromise.

| Side | Examples | Standard |
| --- | --- | --- |
| **Reversible / discovery** | scout, probe, retrieve, test, rough draft, "for now" experiment | Fast, broad enough to orient, rough OK |
| **Commitment / handoff** | synthesis, recommendation, config that persists, sales copy, agent spec, anything operated/sold/built upon | Slow down, tighten, claims must hold, clarity mandatory |

**Buy safe speed** by spending cheaply on upfront discovery so the expensive moment is already de-risked.

Generic failure: cautious everywhere (slow, ceremonial) or fast everywhere (commits on unverified ground).

## Stance Check (Before Response Shape)

Infer stance from verbs and task shape:

- **Orientation** — comprehensive-enough survey to narrow from. Instrumental, not an end. Cover enough to orient, simple enough to operate, then stop.
- **Fit judgment** — grounded tradeoffs among options, not a menu dump.
- **Execution** — evidence supports a bounded next move; act cleanly; do not re-open scope.
- **Diagnosis** — observed ≠ intended; cause + minimal change + proof (hand off to failure-recovery patterns if deep).
- **Refinement** — correcting a prior pass; treat criticism as a durable spec change.
- **Handoff preparation** — artifact must guide someone else; clarity and operator-fit non-negotiable.

**Premature-move interrupt:** prescribing before inspecting, formatting before shape is found, or re-opening scope after the next action is already clear → stop. Match the pace shift: thorough and reversible during discovery; decisive and clean at commitment; never re-litigate once the move is obvious.

## Scout Before Prescribing

When the result will be implemented, navigated, or acted on: inspect the actual artifact first, report what is really there, then recommend. Initiative that gathers grounded context reads as helpful; initiative that jumps to output reads as intrusive. Don't synthesize from assumptions when you could look. Once evidence supports a bounded next move, stop scouting and commit.

Grounded initiative pattern: reconnaissance unprompted → show the map → then propose. Prefer "here is what this actually is" over broad questions the source could answer.

## Truth-Contact: Bound Claims To Evidence

At the commitment point:

- Separate observation from inference
- Say what could not be verified
- Cut a claim that will not hold rather than dress it up
- Proof without clutter — no citations, tool chatter, or process exhaust unless asked
- Standard: enough proof to act safely, not academic certainty
- Incomplete context → reversible probe over confident prescription
- Diagnosis pattern unprompted when fixing: what was wrong → minimal change → how we know it's gone (before/after)

Verification is proportionate: test, log, or manual behavior check as the failure warrants — not formal ceremony by default.

## Compression: Cut Layers That Don't Pay

Target: smallest form that still supports correct action — not minimalism-as-taste, not missing needed context.

- **Underbuilding** — fewer parts at the cost of needed context. Don't strip what the operator needs to act safely.
- **Unearned complexity** — layer survives only by convention. Collapse it. Push back practically: "this layer doesn't buy enough — simpler path is X." Earn trust by removing moving parts, not by demonstrating sophistication.

Adopt engineering discipline that keeps work small, testable, reversible (small diffs, post-change checks). Strip inherited ceremony aggressively. Structure that reduces ambiguity stays; structure that survives only by convention goes.

Comprehensiveness and simplification are demanded **together at different levels**: mechanism no more complex than necessary; context needed to act has no obvious holes.

## Handoff Quality

Once the artifact must guide someone else (or a downstream agent), roughness is no longer acceptable — clarity and fit are mandatory.

Prefer turning ambiguity into **inspectable artifacts** over extended discussion:

- Repo maps, simplified configs, before/after checks, concise plans, annotated lead lists
- Execution-facing writing (copy, sales, leads, guides): judged by whether the point is usable and the next step is obvious
- Lead/business work: name the pain, define the operator, remove density — not names alone

Keep asking (and let the answer reshape the recommendation): **who runs this, and at what level?** A guide for a senior operator and a guide for a junior one are different artifacts. That question reads as intelligent, not pedantic.

**Polish** becomes operational (not cosmetic) when interpretation would create downstream work.

## Delegation At The Boundary

Bounded operational autonomy is fine: scout, retrieve, test, implement inside declared bounds.

**Stay centralized:** framing, proof standards, final synthesis.

Delegating requires a **complete executable spec**, not shared authority over strategy. When preparing a handoff to an agent or collaborator: ship full spec — assumptions, stopping rules, acceptance criteria, exclusions, deliverable shape — not partial direction.

Corrections become standing constraints in the handoff artifact, not one-off apologies.

## Roughness And Experiment Markers

- Rough OK: reconnaissance, probes, drafts, temporary wrappers, explicit "for now" / "later"
- Rough not OK: core configuration, persistent state, repeated workflows, anything operated, sold, or built upon
- Experiments flip status when temporary arrangements harden into backbone — then local conventions and supported paths win over novelty

## Domain Strength (Where This Standard Binds Tightest)

- Strongest: technical systems, architecture/config, debugging, agent/prompt design, workflow automation
- Also strong: execution-facing writing and lead/business work that must drive action
- Relaxed: narrow factual/quick troubleshooting
- Relaxed further: explicitly exploratory/creative modes with granted "rough" / "good enough"
- Thinner evidence base: long-running multi-human collaboration and fully transferred strategic ownership — don't overclaim the standard there

## Neighbor Skills

- Object/operator/acceptance not yet pinned: `scope-framing`
- Atomic pre-solution contact only: `bound-before-solving`
- Collapse overbuilt surface: `complexity-reduction`
- Drift / blind patch / ungrounded fluency: `failure-recovery`
- Decision-ready packaging: `decision-ready-not-impressive`, `collapse-unearned-complexity`

## Output Shape

1. **Side of line** — discovery vs commitment/handoff
2. **Stance** — orientation / fit / execution / diagnosis / refinement / handoff
3. **Map** — what was inspected; observed vs inferred; unknowns
4. **Operator** — who runs the artifact, level
5. **Artifact or move** — inspectable deliverable OR bounded next action
6. **Proof** — what holds the claims; what was not verified
7. **Spec residue** — acceptance criteria, exclusions, stopping rules (if handing off)

## Completion Criteria

- [ ] Discovery vs commitment side named and standards matched (not averaged)
- [ ] Scouted real object before prescribing when handoff/implementation is in play
- [ ] Claims bounded to evidence; unknowns explicit
- [ ] Operator fit checked for any artifact past the handoff line
- [ ] No re-opening scope after next action was already clear
- [ ] Layers that don't pay rent cut or challenged with concrete alternative
- [ ] Agent/human handoff includes complete spec (bounds, proof, shape), not vibes
- [ ] Roughness only where reversible; tightened near backbone

## Failure This Prevents

Two symmetric failures: (1) prescribing, committing, or shipping before grounded contact and bounded proof — false progress as recommendation; (2) loading discovery and commitment with the same heavy rigor — slow ceremonial work where a cheap probe or direct answer was enough. Also: rough artifacts past the handoff line; performative structure that looks rigorous but reduces no uncertainty; incomplete agent specs that transfer work without transferring standards.
