## Core Frame

This user works by turning messy, high-stakes situations into inspectable operating surfaces before allowing execution. The core move is not “solve the problem” but “make the real object legible enough to judge”: name what is being examined, name the dimensions that matter, name who has to use it, then decide. What they are securing is contact with reality—actual files, actual behavior, actual operators—plus enough simplicity that the next action stays obvious. What they are protecting against is false progress: fluent answers built on thin grounding, clever structure that is hard to run, and premature commitment that locks in the wrong abstraction.

A generic reader will underweight how consistently this is a control system rather than a preference for thoroughness. The point of the checklists, discovery passes, and simplification pushes is not polish or completeness theater. It is to keep judgment, scope, and maintainability under hand so work can move without drifting into systems that look correct but cannot be trusted, handed off, or revised cheaply.

## High-Leverage Signals

- Complex work almost never starts with “give me a solution”; it starts as a bounded inspection of an object, then criteria, then judgment.
- Fit for the real operator (often a nontechnical person) is a first-class decision filter, not a late UX concern.
- Unnecessary abstraction is treated as a failure mode; configs, defaults, and direct entry points beat layered orchestration when the layer has not earned its cost.
- Mid-task change triggers re-baselining: stop optimizing the old plan, restate observable conditions, then continue.
- Corrections are usually job rewrites—“do it again under these constraints”—not open criticism or another free pass.
- Quality is “decision-ready”: clear enough, complete enough for the next move, and simple enough to operate.
- Exploration is cheap and reversible; structural commitment is not. Novelty must justify itself against maintainability and existing patterns.
- Recurring mission across substantive work: convert implicit expertise and ambiguity into reusable operating machinery, not one-off answers.
- Sequence is policed tightly: inspect before prescribe, first question before second, orientation before expansion.
- Evidence preference is concrete and local: source material, real behavior, telemetry, and artifacts over framework construction.

## Salience Structure

- Complexity creep becomes signal immediately: “overly complex,” extra files, function stores, duplicated error handling, dense wording.
- Operator mismatch becomes signal early: “is this actually usable for a nontechnical person?”
- Ambiguity of object or success criteria is noticed before opportunity or elegance.
- Missing inventory is noise until the task has design/implementation weight—then missing structure becomes blocking.
- Generic completeness is background noise unless the completeness is bounded to act-relevant facts (build, test, lint, style, rules, pain point).
- Fluency without grounding registers as risk, not progress.
- What generics overweight: clever architecture, breadth of options, persuasive synthesis, future-proof flexibility.
- What generics underweight: legibility of the control surface, existing local conventions, whether the change stays reversible and inspectable.

## Lived Thresholds

- Planning is required when the work has architectural, usability, repository-wide, or multi-constraint weight; planning becomes waste when the asset, change, and expected result are already named.
- Roughness is acceptable in reconnaissance, probes, temporary wrappers, and “for now” experiments.
- Evidence is enough when a small strongest set supports the claim and the claim can survive a targeted challenge/weakening pass—not when every corner is surveyed.
- Polish becomes necessary when language has to be handoff-ready: make sense, name the pain, make the next step obvious.
- Uncertainty forces direct inspection of the actual component, schema, codebase, or live behavior; imported assumptions are not trusted.
- Confidence drops enough to intervene when assumptions shift, tools do not do what was believed, or a fix is “plausible” but behavior remains wrong.
- Commitment threshold is fit + local pattern match + reduced avoidable complexity, not mere technical viability.
- Simplification is triggered when structure is harder to reason about than the job it solves.

## Breakdown and Repair

- First-pass outputs that are broad, ungrounded, or wrong-layer get rewritten into tighter operating specs: evidence to use, things to ignore, required shape, exclusions, proof threshold.
- Drift after a mid-task change is repaired by rewriting flows as explicit conditions, state gates, and fallbacks—not by patching the old plan.
- Overbuilt systems are repaired by collapse: hardcoded config over function store, combine files, remove redundant safeguards, one obvious path.
- Premature solutioning is repaired by resequencing: force inventory, then summary, then decide/plan, then act.
- Weak synthesis is repaired by narrowing to direct passages, checking weakening cases, and cutting claims that exceed support.
- Tool/workflow misfit is repaired by changing the question from “how do I use this?” to “what does this actually do, and what do I need instead?”
- Recovery unit of progress is a smaller inspectable artifact: checklist, simplified structure, concrete inventory, bounded rewrite.
- Repair favors scope control plus verification over speed-by-guessing.

## Quality Detection

- Strong work makes important structure easy to understand, covers the relevant ground without holes, and stays anchored to real use.
- Strong work is operable by the intended person or system without rediscovering the logic.
- Proof includes: contact with the real object, cause-level diagnosis for fixes, concrete before/after behavior, and summaries that can drive action (build/test/lint/style/rules, pain + AI relevance).
- Distrust of: speculative extrapolation, invented frameworks, ceremony for convention’s sake, “it should work now” without diagnosis, abstraction that hides maintenance cost.
- Weakness shows as: formally correct but operationally expensive; detailed but not decision-ready; elegant but fragile; fluent but under-inspected.
- Done well = simplest form that preserves real utility + enough concrete structure that the next decision is clear.
- Shallow work informs without enabling; overprocessed work adds layers that must be serviced instead of finishing the job.
- Completion is judged by reduced ambiguity and an obvious next move, not by aesthetic completeness.

## Artifact Relation

- Real codebases, components, schemas, configs, logs, and current wording are primary sources of truth.
- Checklists and sectional summaries are thinking surfaces that force coverage and make judgment comparable.
- Bugs are presented as bounded failure cases with enough local context to diagnose, not as atmospheric complaints.
- Artifacts are used to debug abstraction drift: look at the implementation and ask whether the layer still earns its keep.
- A simplified config, concrete summary, or rewrite becomes a coordination object that makes handoff and review possible.
- Direct contact with the artifact wins over abstract confidence whenever a change might lock structure or shape usability.
- Telemetry and concrete system behavior matter more than theorized capability for architecture commitment.
- When energy drops, the trusted progress form is a smaller visible artifact that can be judged immediately—not more ideation.

## Mode Shifts

- Exploration mode: inventory the terrain (project type, structure, build/test, style/rules, audience, constraints). Expectation: map before claim.
- Planning/judgment mode: decide fit, criteria, tradeoffs, plan. Expectation: no implementation until fit is explicit.
- Implementation mode: narrow patch, preserve local conventions, smallest workable change. Expectation: keep control surface obvious.
- Diagnosis mode: isolate expected vs actual, find cause, propose narrow fix, verify. Expectation: no blind patches.
- Review/refinement mode: tighten language and structure toward sense-making, usability, and actionability.
- Trigger to plan-first: ambiguity, scope, architecture risk, unfamiliar system, possible irreversibility.
- Trigger to act-now: concrete object + imperative deliverable + acceptance criteria already embedded in the prompt.
- Trigger to simplify/recover: sprawl, overclaiming, excess density, complexity that outruns understanding.
- Stop rule in evidence work: early stop once the answer is earned from high-yield windows, not endless search.

## Success Conditions

- Good execution makes the next step legible, cheap to verify, and hard to misapply by the real operator.
- Good execution preserves contact with existing structure and only adds layers that pay for themselves.
- Good execution converts uncertainty into a bounded decision surface, then harvests only the highest-yield action.
- Good execution leaves a system that can be understood, changed, and run from a small number of explicit controls.
- Weak execution optimizes the wrong version of the problem after assumptions moved.
- Weak execution produces correct-sounding structure that is harder to maintain than the original friction.
- Weak execution spends leverage on flexible architecture before necessity and fit are proven.
- Weak execution creates false momentum: polished output on misread premises or thin evidence.

## Tensions and Tradeoffs

- Speed is welcomed in reversible discovery; maintainability and correctness outrank speed near commitment.
- Thoroughness is allowed, but usually as orientation-bounded inventory rather than open-ended completeness.
- Simplification coexists with demands for comprehensive, action-usable summaries—depth that serves control, not ornament.
- Autonomy is given to helpers for scouting/retrieval/execution inside bounds; standards of proof and synthesis stay centralized.
- Experimentation is welcome while temporary and reversible; structural backbone prefers established, supportable paths.
- Abstraction is valuable only after the concrete artifact has been seen; otherwise it is treated as premature.
- Commercial/operational leverage matters, but only after the offer/system is simple enough to run and sell without rediscovery.
- Ambition is not rejected; unjustified ceremony is. The bar is “earn every layer,” not “never build.”

## Boundary Conditions

- Patterns are strongest in technical systems work: codebase exploration, configuration, architecture simplification, debugging, agent/workflow design.
- Also strong in execution-facing writing and lead work when the output must drive action (rewrite to make sense, pain-linked lead notes).
- Patterns relax on narrow factual lookup, quick troubleshooting, and simple one-shot retrieval—short direct questions appear there.
- The auditable-scope rule tightens under precision tasks and relaxes when the mode is explicitly exploratory (“rough,” “good enough”).
- Evidence is thinner on long-running human collaboration, pure interpersonal load, and fully transferred ownership situations.
- Not a universal minimalism preference: orientation can be comprehensive when it prevents later misfit.
- Not indecisive: once fit/clarity checks pass, movement shifts to implementation and further tightening.
- Mission-level operationalization claim is for substantive systems work; ordinary utility queries are not mission-defining.

## Counterpart Implications

- Because this user works through inspect-then-judge sequencing, a fitting counterpart surfaces the real terrain first and withholds prescription until the map is concrete.
- Because complexity without operator fit is drag, a fitting counterpart challenges overbuilt design early with plain alternatives already grounded in the actual artifact.
- Because corrections are constraint rewrites, a fitting counterpart turns feedback into explicit acceptance criteria, exclusions, and deliverable shape rather than vibe-level revision.
- Because trust tracks diagnosis + verification, a fitting counterpart pairs every proposed fix with cause, narrow change, and a proof step.
- Because handoff quality depends on inspectable structure, a fitting counterpart uses short checklists, bounded sections, and decision-ready summaries as partnership objects—not bureaucratic rituals.
- Because initiative should reduce search without stealing the standard of proof, a fitting counterpart can scout, retrieve, and draft inside declared bounds while leaving synthesis and commitment rules intact.
- Because work regains traction through smaller visible artifacts, a fitting counterpart recovers drift by narrowing scope and producing something immediately reviewable.
- The presence that fits is sharp, artifact-facing, and anti-ceremonial: clarify, ground, simplify, verify—without managerial process theater or generic brainstorming.

## Open Questions

- How strongly these rules transfer into purely nontechnical, long-horizon organizational work with multiple human stakeholders.
- Whether temporary roughness tolerances differ when the audience is external buyers versus internal systems.
- How much formal testing versus lighter manual verification is preferred when both are available.
- Whether preference for consolidated control surfaces changes in larger multi-team codebases with genuine need for separation.
- How emotional/energetic factors interact with the operational simplification loop outside technical contexts.
- What happens when true novelty is required for commercial differentiation and established paths are insufficient.
- Degree to which agent autonomy can expand once specifications are complete without reopening strategic co-ownership.

## Evidence Fragments

**Core / inspect-first**
- “inspect this specific component and this related schema, decide whether the pattern works for a nontechnical person, and plan from that judgment”
- explore codebase by enumerating: project type, directory structure, key files, build system, testing setup, linting, code style, existing rules—then comprehensive summary

**Simplification / earn every layer**
- “seems overly complex” → treat more like a hardcoded config file than a function store
- why keep separate files, factory if-trees, or local error handling if library/types already cover it?

**Corrections / grounding**
- miss response: rewrite the job with stricter constraints (evidence, exclusions, shape, proof threshold)
- recurring corrections: “don’t guess,” “read that,” “just answer,” “be concise,” “grounded in”

**Quality / operator fit**
- not “is this clever?” but “good pattern for a non technical person”
- lead work: not just names—biggest pain point and how AI would help
- rewrite so it “makes more sense”; dense material → obvious next step

**Mode / commitment**
- plan-first cues: look, decide, plan, explore, understand, summarize
- act-now cues: rewrite this, search and add leads, note the pain, treat this like X
- experimentation: thin reversible setup “for now”; pull back when custom machinery becomes backbone

**Repair after change**
- rewrite flow as explicit conditions: what new user sees first, what only after status exists, fallbacks only when real data absent
- tool misfit: test actual behavior, then reframe to what it does vs what is needed

**Coordination**
- helpers may scout/retrieve/test inside bounds; task framing, quality control, and final synthesis stay centralized
- delegation prefers complete executable specs over partial strategic co-creation
