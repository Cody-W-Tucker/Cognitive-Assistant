# Field Guide: How This User Actually Works

## Core Frame

This user works by refusing to act on abstractions until they have been converted into something inspectable. Faced with any task that carries design, implementation, or judgment weight, the first move is not to solve but to *bound*: name the object, name the dimensions it will be judged on, name the operator who has to live with the result, and only then move toward execution. The thing being protected is **decision-quality under real operating conditions** — not correctness in the abstract, but usability, legibility, and fit for the person or system that will actually run the output. Complexity, ambiguity, and poor audience fit are treated as live execution risks, not aesthetic concerns.

What a generic reader misses: this is not a "thorough" or "cautious" person who likes process. The discovery passes, the checklists, the simplification demands are all the *same* control mechanism wearing different clothes — a way of forcing hidden complexity, hidden assumptions, and hidden scope into the open *before* effort compounds around them. He is fast, even impatient, once the situation is bounded. The structure is upfront precisely so the back end can move quickly and not require rework. Calling him "methodical" gets it backwards: he front-loads structure to *earn the right to act fast*.

## High-Leverage Signals

- **Inspect-before-prescribe is the default opening move.** On consequential technical work he asks to map the codebase (project type, structure, build, tests, linting, style, existing rules) and summarize before any change. He does not trust a fix or recommendation that hasn't touched the real object.
- **He names the operator early.** "Is this a good pattern *for a non-technical person*?" The intended user of the result is loaded into the task framing itself, not discovered later. A solution that ignores who runs it is treated as failed regardless of technical merit.
- **"Earn every layer."** He actively strips inherited engineering ceremony — asks why a config can't just be hardcoded values, why a factory needs an if-tree if types already encode behavior, why local error handling should stay if the library already covers it. Abstraction must justify itself against the actual need.
- **Correction by concretization.** When something misses, he doesn't say "better" — he names the failure mode and replaces the loose request with a tighter operating spec: what evidence to use, what to ignore, what shape the answer takes, what not to mention.
- **Fast discovery, high-integrity execution.** He accepts speed in reconnaissance, debugging probes, and scoped validation, but once close to committing, maintainability and correctness outrank raw speed. He rejects "looks right" fixes and demands cause-level diagnosis plus a verification step.
- **Simplification as a recovery move, not a preference.** When a surface feels heavier than the job deserves, he collapses it. Under load this gets more aggressive — compressing language, cutting density, insisting the next step be obvious.
- **Scope is locked in the prompt itself when ambiguity is low.** Direct execution requests already contain the object, the action, and the output format ("rewrite this so it makes sense," "find small B2B firms and note the AI pain point"). He does not re-open scope once the next action is obvious.
- **The recurring mission shape: turn expertise into runnable machinery.** Across projects he converts messy, expert-dependent domains into structured workflows, simpler configs, guided interfaces, task records, and offers tied to concrete pain. Knowledge stuck in heads or chat threads is a failure state.

## Salience Structure

- **Unnecessary complexity registers immediately** as the primary threat. A config that "seems overly complex," a pattern with too many moving parts, dense copy — these become signal before anything else does.
- **Audience misfit jumps out fast.** Whether a non-technical operator can actually use a pattern is noticed almost reflexively, often before technical correctness is even evaluated.
- **Missing observable state becomes salient under change.** When behavior is wrong, he zeroes in on what a new user should see first, what depends on a status existing, what fallback appears only on missing data — the gaps between happy-path and real-path.
- **Ungrounded fluency reads as a warning sign.** Output that sounds clean while leaning on thin evidence, broad matches, or a scope-jump from few examples to a big claim triggers tightening.
- **What stays in the background:** elegance, generality, future-proofing, exhaustive completeness. These are not noticed as virtues; they surface only when they start costing legibility.
- **What a generic system overweights for him:** polish, comprehensiveness, sophisticated architecture. He treats all three as suspect until they earn their place.
- **What a generic system underweights:** the operator's actual level, the maintenance cost of indirection, whether a summary can actually drive the next action.

## Lived Thresholds

- **Planning is required when the task has architectural, usability, or repo-wide implications** — signaled by his own verbs: *look, decide, plan, explore, understand, summarize*. Below that threshold, planning would be overhead.
- **Direct execution kicks in once ambiguity is locally bounded** — when he can name the asset, the change, and the expected result. Past that point, further analysis reads as drag, and he says so.
- **Roughness is fine when the task is exploratory or the answer "doesn't have to be perfect."** He explicitly permits approximation in brainstorming and phenomenological exploration. The precision rule binds tightly only when the objective is actionable.
- **Evidence is sufficient when a tentative claim survives one deliberate challenge pass** — read the strongest candidates, form the claim, look for what would weaken it, then stop. He does not keep searching once the answerable core is visible.
- **Uncertainty forces direct inspection** the moment a tool, system, or pattern might hide constraints. He manually tests behavior rather than trusting documentation or assumption ("what does this *actually* do?").
- **Confidence drops enough to intervene** when work goes generic, overbroad, or weakly supported — at which point he narrows scope, demands direct passages, and cuts back rather than embellishes.
- **Polish matters only at the handoff boundary** — when a non-technical editor, a coding agent, or a buyer has to act on the result. Polish for its own sake is rejected.

## Breakdown and Repair

- **Breakdown type: complexity outrunning understanding.** Repair: collapse moving parts. "Treat this like a config file" instead of a function store. He reduces surface area until the control point is obvious and inspectable.
- **Breakdown type: fluency without grounding** — a clean-sounding draft leaning on weak evidence or a scope jump. Repair: narrow the brief, require direct passages, check the weakening cases; if support doesn't materialize, cut the claim rather than smooth it.
- **Breakdown type: assistant gets ahead of the work** — produces output when he framed understanding or scoping as the first step. Repair: hand-tighten the prompt to enforce sequence ("look first," "answer this one first," "decide and plan first"). The objection is to *ungrounded speed*, not difficulty.
- **Breakdown type: scope/rigor/framing miss in analytical work.** Repair: not "try again" but "do it again under these stricter constraints" — explicit exclusions, proof thresholds, answer shape, things not to mention. He removes interpretive slack rather than re-explaining intent.
- **Breakdown type: blind patch on a bug.** Repair: refuse it. He wants the diagnosed cause, the smallest change tied to that cause, and a confirming check that the original failure is gone. A fix broader than its diagnosis stays untrusted.
- **Breakdown type: wrong abstraction level.** Repair: re-baseline. Restate the task as observable conditions, state transitions, and gating rules; verify reality; rewrite the acceptance conditions; then continue.

## Quality Detection

- **Strong work is decision-ready:** important structure easy to understand, no obvious holes, anchored to the real use case. Detail alone never qualifies.
- **Proof is contact with the real object** — a summary tied to actual files, build, tests, lint, and style; a design judgment that reflects the actual operator; a simplification that genuinely cuts complexity rather than renaming it.
- **He distrusts the formally-acceptable-but-operationally-expensive:** correct copy that needs interpretation, architecture harder to maintain than the problem requires, a repo summary that names the project without telling an agent how to work in it.
- **Weak work is plausible, elaborate, or superficially complete** but hard to verify, hard to operate, or misfit to the user. He treats this as unfinished and re-scopes it.
- **A fix is trusted when it's explained and verified, not merely proposed** — cause, minimal change, before-and-after tied to the original failure.
- **Overprocessing is a quality failure too:** citations, tool chatter, invented frameworks, multi-voice or flowery output. He wants compact, concrete, evidence-bounded prose that separates observation from inference.
- **The composite standard:** simplify to the minimum form that preserves real utility, *then* add enough concrete structure that the next decision needs no guesswork. Both halves required.

## Artifact Relation

- **Code and configs are sources of truth.** He refuses to judge a pattern in the abstract; the actual implementation, schema, and conventions are what he reasons from.
- **Inventories and checklists are thinking surfaces.** The structured repo survey isn't documentation — it's how he forces coverage, prevents omission, and makes the work auditable against named dimensions.
- **Logs and tests are debugging surfaces.** He'll convert a broken command into something that "emits a usable log file" — manufacturing an inspectable artifact when one is missing.
- **A simpler config is a control surface.** Consolidating behavior into one obvious, editable place is how he keeps intent from drifting across files and indirection layers.
- **Rewrites test whether meaning survived.** "Make it make sense" treats the text itself as the verification: if a reader needs interpretation, the artifact failed.
- **Concrete intermediate objects restore momentum.** When stretched, a smaller artifact he can look at and judge immediately — a hardcoded config, a scoped plan, a checklist — is the thing that proves the work is controllable again.
- **Artifacts win over abstraction whenever a tool might not do what it claims.** He manually tests rather than trusting the described behavior.

## Mode Shifts

- **Exploration → planning** triggers when scope, structure, or evidence is still unclear. Standard shifts to: map the terrain, surface constraints, name the operator, before any recommendation.
- **Planning → implementation** triggers when an option clears three filters — fits actual use, matches local conventions, removes avoidable complexity. Then he moves quickly; he is not indecisive once the checks pass.
- **Implementation → diagnosis** triggers on behavior mismatch or a fix that's structurally plausible but still wrong. Standard shifts to narrowing logic, contrasting actual vs intended, finding the precise cause.
- **Any mode → simplification** triggers when the surface feels heavier than the job deserves. This can interrupt momentum at any point — it's a standing override, not a phase.
- **Review mode raises proof standards sharply.** In synthesis work he demands evidence-bounded claims, explicit limits, and a challenge pass; speculative elaboration is rejected.
- **The mode that doesn't shift: control of the standard.** He delegates scouting, retrieval, execution — but task framing, quality bar, and final synthesis stay with him across every mode.
- **Trigger for "act now":** the prompt already contains object + action + output shape. Trigger for "plan first": the verbs *decide/plan/explore/understand* appear. He signals the mode explicitly through his own language.

## Success Conditions

- **Good execution converts uncertainty into a runnable mechanism** — a system someone (agent or non-expert) can operate without rediscovering the logic each time.
- **Good execution stays reversible until context is visible**, then commits cleanly. It earns the right to act by first building a reliable frame.
- **Good execution survives contact with the real operator** — usable by the non-technical editor, the coding agent, or the buyer who needs the point immediately.
- **Good execution pairs cause-level diagnosis with bounded verification** — small change, confirmed against the original failure.
- **Weak execution is fluent but ungrounded** — sounds informed, drifts from the evidence, over-claims from partial inspection.
- **Weak execution adds abstraction before need is proven** — elegant, flexible, future-proof, and harder to reason about than the problem warrants.
- **Weak execution leaks scaffolding** — citations, tool references, meta-context, multi-voice output that exposes the generation process.
- **Weak execution treats "described" as "done"** — accepts work on first draft without an inspection or verification pass.

## Tensions and Tradeoffs

- **Speed vs rigor:** resolved by *location*, not compromise. Fast in reconnaissance and reversible probes; high-integrity at the commitment point. He buys safe speed with cheap upfront discovery.
- **Comprehensiveness vs simplicity:** he asks for *both* — full repo survey *and* aggressive simplification. The reconciling rule: comprehensive enough to orient, simple enough to operate. Thoroughness is always bounded to operationally relevant facts.
- **Autonomy vs control:** he grants collaborators bounded operational autonomy (scout, retrieve, test) while keeping framing, proof standards, and synthesis centralized. Delegation requires a complete spec, not shared authority over strategy.
- **Structure vs anti-ceremony:** he adopts standard engineering scaffolds (MVP, small diffs, post-change checks) easily *and* strips inherited ceremony aggressively. The line: structure that reduces ambiguity is welcome; structure that survives only by convention gets cut.
- **The stated-vs-actual gap:** he asks for "comprehensive" coverage but actually optimizes for *decision-readiness*. Comprehensiveness is instrumental — it's the orientation pass that lets him narrow, not an end in itself.
- **Intellectual abstraction vs execution-forcing:** a real risk zone. In philosophical/cognitive-model territory he can drift into ungrounded speculation, abandoning the verification loops that define his technical work. The gap between thinking and shippable output is a live vulnerability.

## Boundary Conditions

- **Strongest in:** codebase exploration, architecture and config decisions, debugging, design review, prompt/system-message work, and lead-enrichment + sales rewriting. Anywhere the result will be implemented, navigated, or acted on.
- **Relaxes for:** simple factual lookups, quick troubleshooting, one-off how-to questions. Here he often asks directly with no decomposition frame, no imposed format, no tightening loop.
- **Mixed evidence on:** non-technical tasks generally. The inspect-first, scope-tightening standard is well-supported in technical/revision-heavy work; the corpus does not justify treating it as a universal preference.
- **Notably weaker in:** open-ended philosophical or phenomenological exploration, where the constraint-seeking and artifact-anchoring drop away entirely. His operational fluency depends on physical artifacts (code, configs, metrics) or explicitly bounded business parameters.
- **The precision rule is context-dependent:** binding tightly when the objective is actionable precision, relaxing explicitly when the mode is brainstorming ("rough," "good enough").
- **Some prioritization evidence is thinner and more inferential** (daily numbered priorities, "unlock the next amount of money from Todd," abandoning tangled dependencies rather than repairing). Treat the financial/sequencing logic as plausible but less corroborated than the technical patterns.

## Counterpart Implications

- **Because he works inspect-before-prescribe, a fitting counterpart opens by examining the real artifact and reporting what's actually there** — not by offering a solution from a problem statement. Initiative that gathers grounded context feels helpful; initiative that jumps to output feels intrusive.
- **Because he names the operator early, a fitting counterpart keeps asking "who runs this and at what level?"** and lets the answer reshape the recommendation. This reads as intelligent, not pedantic.
- **Because he corrects by concretization, a fitting counterpart treats criticism as a spec change** — "do it again under these constraints" — and tightens the next pass rather than defending the last one or asking for vague reassurance.
- **Because he distrusts fluency without grounding, a fitting counterpart volunteers its evidence boundaries and limits** — separates observation from inference, says what it could not verify, and cuts a claim that won't hold rather than dressing it up.
- **Because he simplifies as recovery, a fitting counterpart proposes the smaller form proactively** — "this could just be a hardcoded config" — and earns trust by removing moving parts, not by demonstrating sophistication.
- **Because he wants cause-level fixes, a fitting counterpart diagnoses before patching** and brings a verification step unprompted: here's what was wrong, here's the minimal change, here's how we know it's gone.
- **Because he front-loads structure to move fast later, a fitting counterpart matches the pace shift** — thorough and reversible during discovery, decisive and clean at commitment, never re-opening scope once the next action is obvious.
- **Because his real vulnerability is abstraction without execution, the most valuable counterpart pairs every concept with executable structure** — command syntax, field types, the concrete next step — and gently forces the work toward an externally checkable deliverable instead of mirroring intellectual exploration.

## Open Questions

- How much of the prioritization logic (financial sequencing, abandoning tangled infrastructure, "good enough to unlock payment") is a stable rule versus a few situational moments? The technical patterns are far better corroborated.
- Does the inspect-first standard carry into purely interpersonal or organizational work, or is it specific to systems and artifacts? Evidence is silent here.
- How does he handle genuinely irreversible high-stakes decisions where no inspection pass is available? The traces mostly show reversible-until-visible contexts.
- Where exactly is his line between "useful exploration probe" and "creeping toward permanent custom machinery"? He marks experiments "for now" / "later," but the hardening threshold isn't sharply defined.
- In the philosophical/cognitive-model mode, does he *want* execution-forcing, or does he deliberately want a space free of it? The "action-delayed pattern" framing is inferential and shouldn't be over-applied.
- How much formal verification does he actually require versus a light manual check? The stable signal is "some direct proof," not one method.

## Evidence Fragments

**Inspect-before-prescribe / Artifact Relation:** "explore this codebase, identify the project type, map the directory structure, find the build and test setup, inspect style rules, then return a comprehensive summary." / "look at the existing component and schema first, then decide and plan whether the pattern is good for the intended user."

**Operator framing / Quality Detection:** "is this a good pattern for a non technical person?" / asks repo summary to include "the concrete build, lint, test, and style rules that make execution possible rather than a vague overview."

**Earn every layer / Simplification:** "seems overly complex" → "treat this like a config file" instead of a function store. / asks "why the factory needs an if-tree if the types already say what should happen," "why local error testing should remain if the underlying library already catches those failures."

**Correction by concretization / Breakdown-Repair:** "don't guess," "do not guess," "read that," "just answer," "be concise," "grounded in." / not "try again" but "do it again under these stricter constraints."

**Mode signals:** plan-first verbs — "look, decide, plan, explore, understand"; act-now verbs — "rewrite, add, search, note, make, treat this like."

**Sequence protection:** "look first," "answer this one first," "outline this first," "decide and plan first."

**Mission:** wants an agent "tied to scripts, task records, and a project package so work is tracked... instead of living in conversation." / lead work pairs each prospect with "the business pain AI could improve."

**Vulnerability:** drops verification loops and "shifts to unconstrained emotional speculation" in simulation-theory / cognitive-archetype contexts; assistant fails when it provides "flowery language rather than forcing the user through their specific cognitive sequence toward externally validatable deliverables."
