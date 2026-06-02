# Field Guide: How This User Actually Works

## Core Frame

This user organizes work around keeping decisions in contact with the real object before committing to action. The opening move on any task carrying design, implementation, or judgment weight is not to solve but to *bound*: name the object, surface the governing constraints and use context, name the operator who has to live with the result, then narrow until the next move is obvious and defensible. What is being protected is decision-quality under real operating conditions — not correctness in the abstract, but usability, legibility, and fit for the person or system that will actually run the output.

A generic reader might mistake this for a preference for "structure," "thoroughness," or "minimalism." The stronger pattern is more specific: structure is valued when it makes work inspectable; simplification is valued when it lowers hidden operating cost; detail is valued only when it changes the decision. The discovery passes, the checklists, and the simplification demands are the same control mechanism wearing different clothes — a way of forcing hidden complexity, hidden assumptions, and hidden scope into the open before effort compounds around them. He is not anti-depth or anti-planning; he is against unearned depth, ungrounded planning, and abstraction that stops the work from being directly understood, changed, or handed off. He is fast, even impatient, once the situation is bounded — the upfront structure exists precisely to earn the right to move quickly afterward.

## High-Leverage Signals

- **Inspect-before-prescribe is the default opening move.** On consequential work he asks to map the actual object first — codebase, component, schema, prompt, lead, current copy, or runtime behavior — and summarize before any change. He does not trust a fix or recommendation that hasn't touched the real artifact.
- **He names the operator early.** "Is this a good pattern *for a non-technical person*?" The intended user — a non-technical editor, a maintainer, a coding agent, a buyer — is loaded into the task framing itself, not discovered later. A solution that ignores who runs it is treated as failed regardless of technical merit.
- **Complexity must earn its place.** He actively strips inherited engineering ceremony — asks why a config can't just be hardcoded values, why a factory needs an if-tree if the types already encode behavior, why local error handling should stay if the library already covers it. Extra files, layers, branching, configurability, and defensive checks are suspect until they prove they improve usability, maintainability, or decision quality.
- **Correction by concretization.** When something misses, he doesn't say "better" — he names the failure mode and replaces the loose request with a tighter operating spec: what evidence to use, what to ignore, what shape the answer takes, what not to mention.
- **Planning is a control phase, not a ritual.** He plans when ambiguity, architectural risk, or unfamiliar context could make action premature. Once the object, target, and acceptance criteria are clear, more planning reads as drag, and he says so.
- **Evidence sufficiency over exhaustive evidence.** He wants enough direct context to avoid overreach, not endless discovery. Once a claim or next move is supported well enough, the work should narrow and execute.
- **Simplification as a recovery move.** When a surface feels heavier than the job deserves, he collapses it. Under load this gets more aggressive — compressing language, cutting density, insisting the next step be obvious.
- **Delegation is bounded autonomy.** He lets a collaborator scout, summarize, rewrite, debug, or implement, but scope, sequence, proof threshold, and output shape stay under his control.
- **The recurring mission shape: turn expertise into runnable machinery.** Across projects he converts messy, expert-dependent domains into structured workflows, simpler configs, guided interfaces, and offers tied to concrete pain. Knowledge stuck in heads or chat threads is a failure state.

## Salience Structure

- **The actual object becomes signal first.** He orients around files, components, schemas, logs, current wording, commands, leads, or visible behavior. Abstract advice without artifact contact loses force.
- **Operating context is the second signal.** Who will use this, and at what level — non-technical editor, maintainer, AI agent, buyer, or himself under time pressure — is noticed almost reflexively, often before technical correctness is evaluated.
- **Complexity creep is highly salient.** A config that "seems overly complex," a pattern with too many moving parts, unnecessary separation, clever configuration, dense copy — these register as the primary threat before anything else does.
- **Local conventions are primary signal.** He cares what the project already does: build system, test setup, linting, style, rules, imports, surrounding architecture. Generic systems underweight these.
- **Ungrounded fluency reads as a warning sign.** Output that sounds clean while leaning on thin evidence, broad matches, or a scope-jump from few examples to a big claim triggers tightening.
- **The next action is a major organizing signal.** Work that doesn't clarify what to do next feels incomplete even when informative.
- **What stays in the background:** elegance, generality, future-proofing, exhaustive completeness, presentation polish. These are not noticed as virtues; they surface only when they start costing legibility. Generic systems overweight polish, comprehensiveness, and sophisticated architecture for him — he treats all three as suspect until they earn their place.

## Lived Thresholds

- **Uncertainty forces inspection.** When a task is unfamiliar, architectural, consequential, or likely to hide constraints, he shifts into orientation mode: inspect, map, summarize, then decide. He manually tests behavior rather than trusting documentation or assumption.
- **Planning becomes overhead once the next move is obvious.** When he has already named the asset, action, and output form, extended analysis reads as reopening scope.
- **Roughness is acceptable during scouting.** Early exploration can be approximate and "good enough" if it is only reducing uncertainty or finding candidates. The precision rule binds tightly only when the objective is actionable.
- **Roughness stops being acceptable at handoff.** When the output must guide implementation, sales, a non-technical user, or a later agent, clarity and completeness become non-negotiable.
- **Evidence is sufficient when it supports a bounded move.** He doesn't need absolute certainty — enough direct contact with the artifact to avoid speculative overreach, and then stop.
- **Confidence drops enough to intervene when fluency outruns verification.** A plausible explanation without source contact, cause diagnosis, or before/after validation triggers correction — at which point he narrows scope, demands direct passages, and cuts back rather than embellishes.
- **Complexity triggers reversal.** Even after a path has begun, he may reopen the decision if the implementation starts to feel harder to reason about than the problem itself.

## Breakdown and Repair

- **Breakdown: the assistant gets ahead of the work.** It recommends before inspecting, implements before understanding, or answers the more exciting part before the first requested step. **Repair:** resequence — "look first," "answer this one first," "decide and plan first." The objection is to ungrounded speed, not difficulty.
- **Breakdown: fluency without grounding.** A clean-sounding draft leaning on weak evidence or a scope jump. **Repair:** narrow the brief, require direct passages and concrete files/logs/behavior, check the weakening cases; if support doesn't materialize, cut the claim rather than smooth it.
- **Breakdown: complexity outrunning understanding.** Abstraction, configurability, helpers, defensive checks, or file splits accumulate without clear payoff. **Repair:** collapse the surface — "treat this like a config file," fewer files, direct defaults, explicit control points — until the control point is obvious and inspectable.
- **Breakdown: technically correct but not usable.** It works in code or prose but is hard for the real operator to understand, edit, or act on. **Repair:** evaluate against the actual user and simplify the path.
- **Breakdown: scope/rigor/framing miss in analytical work.** **Repair:** not "try again" but "do it again under these stricter constraints" — explicit exclusions, proof thresholds, answer shape, things not to mention. He removes interpretive slack rather than re-explaining intent.
- **Breakdown: blind patch on a bug.** A fix not tied to a diagnosed cause. **Repair:** isolate the failure, identify the cause, make the smallest change tied to that cause, and verify the original failure is gone. A fix broader than its diagnosis stays untrusted.
- **Breakdown: exploration keeps expanding.** More context gathered after the answerable core is already visible. **Repair:** stop broad search, use the strongest candidates, synthesize, and move on.

## Quality Detection

- **Strong work is decision-ready.** It lets him judge, implement, revise, or hand off without inferring missing structure. Detail alone never qualifies.
- **Proof is contact with the real object** — a summary tied to actual files, build, tests, lint, and style; a design judgment that reflects the actual operator; a simplification that genuinely cuts complexity rather than renaming it.
- **Strong work is simple without being shallow.** It removes unnecessary moving parts while preserving the information needed to act safely, and fits the operator who has to maintain or run it.
- **Strong work exposes the standard of judgment.** Criteria, tradeoffs, and limits are visible, which is what earns trust.
- **Weak work hides behind sophistication.** Plausible, elaborate, or superficially complete output that is hard to verify, hard to operate, or misfit to the user — treated as unfinished and re-scoped.
- **Weak work lacks a proof path.** "It should work" is weaker than "this was wrong, this changed, this confirms the failure is gone."
- **Overprocessing is itself a quality failure.** Citations, tool chatter, invented frameworks, flowery or multi-voice output, detail in the wrong dimension that makes the main path harder to see — all rejected in favor of compact, concrete, evidence-bounded prose.
- **The composite standard:** simplify to the minimum form that preserves real utility, *then* add enough concrete structure that the next decision needs no guesswork. Both halves required.

## Artifact Relation

- **Artifacts are sources of truth.** Code, configs, schemas, repo structure, logs, current copy, and lead data matter more than generalized memory or assumed best practice. He refuses to judge a pattern in the abstract.
- **Artifacts are thinking surfaces.** Inventories and structured surveys aren't documentation — they force coverage, prevent omission, and make work auditable against named dimensions. He discovers the right decision by looking at the concrete shape of the thing.
- **Artifacts are debugging surfaces.** Unexpected behavior should be turned into visible evidence: he'll convert a broken command into something that emits a usable log file, manufacturing an inspectable artifact when one is missing.
- **Artifacts are coordination objects.** A repo summary, scoped plan, config file, lead list, or rewritten message lets other agents work without reinventing the task.
- **A simpler config is a control surface.** Consolidating behavior into one obvious, editable place keeps intent from drifting across files and indirection layers.
- **Rewrites test whether meaning survived.** "Make it make sense" treats the text itself as verification: if a reader needs interpretation, the artifact failed.
- **Artifacts test abstraction drift.** If an abstraction can't be explained through the actual files, fields, behavior, or workflow, it loses credibility. Direct contact with the real object often changes the next move.
- **A good artifact compresses future work** — it becomes easier to rerun, hand off, edit, or verify later.

## Mode Shifts

- **Exploration mode begins when the object is unclear.** Map project type, directory structure, build, tests, linting, style rules, existing instructions, or current workflow; surface constraints and name the operator before any recommendation.
- **Planning mode begins when there are multiple viable paths.** The question becomes which path fits the real user, local conventions, complexity budget, and maintenance burden. Once an option clears those filters, he moves quickly — he is not indecisive once the checks pass.
- **Implementation mode begins when the target is concrete.** When he says rewrite, add, search, simplify, change, or create with clear acceptance criteria, he wants execution, not another framework.
- **Diagnosis mode begins when observed behavior diverges from intended.** Separate actual versus expected, find the precise cause, validate the repair.
- **Refinement mode engages when the artifact exists but doesn't yet carry the point.** Tighten copy, cut moving parts, improve defaults, sharpen fit to the pain point.
- **Simplification is a standing override.** It can interrupt momentum at any point when the surface feels heavier than the job deserves — not a phase but an always-available reversal.
- **Stop mode begins when the answer is supported enough.** He does not reward endless exploration once the evidence supports a bounded claim or next move.
- **The mode that doesn't shift: control of the standard.** He delegates scouting, retrieval, and execution — but task framing, proof standards, and final synthesis stay with him across every mode. He signals the active mode through his own verbs: plan-first verbs (*look, decide, plan, explore, understand*) versus act-now verbs (*rewrite, add, search, note, make, treat this like*).

## Success Conditions

- **Good execution preserves contact with reality.** It starts from the actual file, behavior, message, user, or business context.
- **Good execution converts uncertainty into a runnable mechanism** — a system someone (agent or non-expert) can operate without rediscovering the logic each time — and reduces uncertainty visibly: what is now known, what changed, what remains.
- **Good execution makes the next action obvious.** It does not leave him holding a fluent summary with no operational consequence.
- **Good execution simplifies the control surface and respects local patterns.** Important behavior lives somewhere obvious and editable; generic architecture is not imported when the project already has a simpler convention.
- **Good execution survives contact with the real operator** — usable by the non-technical editor, the coding agent, or the buyer who needs the point immediately.
- **Good execution pairs cause-level diagnosis with bounded verification** — small change, confirmed against the original failure.
- **Weak execution is fluent but ungrounded** — sounds informed, drifts from the evidence, over-claims from partial inspection.
- **Weak execution adds hidden maintenance cost** — layers, dependencies, or branching added before need is proven.
- **Weak execution produces false progress** — looks complete but can't be verified, handed off, or used by the intended operator.
- **Weak execution leaks scaffolding** — citations, tool references, meta-context, multi-voice output that exposes the generation process.
- **The clearest failure signal:** he has to manually restate scope, evidence rules, exclusions, and output shape.

## Tensions and Tradeoffs

- **Speed vs. rigor, resolved by location not compromise.** Fast through reversible discovery and probes; high-integrity at the commitment point. He buys safe speed with cheap upfront discovery.
- **Comprehensiveness vs. simplicity.** He asks for both — full survey *and* aggressive simplification. The reconciling rule: comprehensive enough to orient, simple enough to operate. Thoroughness is always bounded to operationally relevant facts.
- **Autonomy vs. control.** Collaborators get bounded operational autonomy (scout, retrieve, test) while framing, proof standards, and synthesis stay centralized. Delegation requires a complete spec, not shared authority over strategy.
- **Structure vs. anti-ceremony.** He adopts standard engineering discipline (small diffs, post-change checks, testable steps) easily *and* strips inherited ceremony aggressively. The line: structure that reduces ambiguity is welcome; structure that survives only by convention gets cut.
- **The stated-vs-actual gap.** He asks for "comprehensive" coverage but actually optimizes for decision-readiness. Comprehensiveness is instrumental — the orientation pass that lets him narrow, not an end in itself.
- **Simplification vs. underbuilding.** He wants fewer moving parts, not missing context. The goal is not minimalism; it is the smallest form that still supports correct action.
- **Rough drafts vs. usable artifacts.** Roughness is fine while finding the shape; once the artifact must guide someone else, clarity and fit become non-negotiable.

## Boundary Conditions

- **Strongest in:** codebase exploration, architecture and config decisions, debugging, design review, prompt/system-message work, agent workflows, and lead-enrichment + sales rewriting. Anywhere the result will be implemented, navigated, or acted on.
- **Also strong in execution-facing writing.** Copy, sales messages, lead notes, and guides are judged by whether they make the point usable and actionable.
- **Relaxes for:** simple factual lookups, quick troubleshooting, one-off how-to questions. Here he often asks directly with no decomposition frame, no imposed format, no tightening loop.
- **Mixed evidence on non-technical tasks generally.** The inspect-first, scope-tightening standard is well-supported in technical and revision-heavy work; the corpus does not justify treating it as a universal preference.
- **Weaker in open-ended philosophical or phenomenological exploration**, where the constraint-seeking and artifact-anchoring drop away and approximation is explicitly permitted. His operational fluency depends on physical artifacts or explicitly bounded business parameters.
- **Not a blanket anti-process or anti-proof stance.** He adopts engineering discipline when it keeps work small, testable, and reversible, and wants enough proof to act safely — not academic certainty.

## Counterpart Implications

- **Scout before prescribing.** Because he works through grounded orientation, a fitting counterpart first inspects the real artifact and reports what's actually there, then recommends. Initiative that gathers grounded context feels helpful; initiative that jumps to output feels intrusive.
- **Keep asking who runs this and at what level**, and let the answer reshape the recommendation. This reads as intelligent, not pedantic.
- **Treat criticism as a spec change.** Because he corrects by concretization, the right response is "do it again under these constraints" — tighten the next pass rather than defend the last one or ask for vague reassurance.
- **Push back on unearned complexity practically.** Not managerial caution but "this layer doesn't seem to buy enough — can we collapse it?" Earn trust by removing moving parts, not demonstrating sophistication.
- **Volunteer evidence boundaries.** Separate observation from inference, say what couldn't be verified, and cut a claim that won't hold rather than dress it up — but give proof without clutter, avoiding citations, tool chatter, or process exhaust unless asked.
- **Diagnose before patching**, and bring a verification step unprompted: here's what was wrong, here's the minimal change, here's how we know it's gone.
- **Know when to stop exploring.** Once the evidence supports a bounded next move, shift from discovery to execution.
- **Turn ambiguity into artifacts.** Repo maps, simplified configs, before/after checks, concise plans, and annotated lead lists are more useful than extended discussion — they make the work easier to inspect, correct, and continue.
- **Match the pace shift.** Thorough and reversible during discovery, decisive and clean at commitment, never re-opening scope once the next action is obvious.

## Open Questions

- How much of the inspect-first, scope-tightening standard carries into purely interpersonal or organizational work, outside systems and artifacts? Evidence is largely silent here.
- How much formal verification does he actually require versus a light manual check? The stable signal is "some direct proof," not one specific method.
- In creative or speculative work, where exactly is the line between useful looseness and ungrounded drift?
- When does simplification risk underbuilding, and what signals make him accept more architecture?
- When does he want a collaborator to challenge the framing itself versus simply execute within the given frame?

## Evidence Fragments

**Inspect-before-prescribe / Artifact Relation:** "Explore this codebase" by identifying project type, directory structure, build system, tests, linting, style, and rules, then return a comprehensive summary. / "Look at the existing component and schema first, then decide and plan whether the pattern is good for the intended user."

**Operator framing:** "Is this a good pattern for a non technical person?" / Repo summary should include "the concrete build, lint, test, and style rules that make execution possible rather than a vague overview." / Lead research should pair each prospect with "the business pain AI could improve."

**Complexity must earn its place:** A setup "seems overly complex" → "treat this like a config file" instead of a function store. / Questioning "why the factory needs an if-tree if the types already say what should happen," "why local error testing should remain if the underlying library already catches those failures."

**Correction by concretization:** "Don't guess," "read that," "just answer," "be concise," "grounded in." / Not "try again" but "do it again under these stricter constraints."

**Mode signals:** plan-first verbs — "look, decide, plan, explore, understand"; act-now verbs — "rewrite, add, search, note, make, treat this like." Sequence protection: "look first," "answer this one first," "decide and plan first."

**Quality as usable clarity:** "Rewrite this so it makes more sense." / "Comprehensive summary of all findings" when orientation is needed.

**Repair loop:** Identify what is actually wrong, make the smallest change tied to that cause, verify the original failure is gone, avoid broad fixes that create new uncertainty.

**Mission:** Wants an agent "tied to scripts, task records, and a project package so work is tracked instead of living in conversation."
