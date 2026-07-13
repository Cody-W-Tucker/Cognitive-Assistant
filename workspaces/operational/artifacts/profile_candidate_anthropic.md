# Field Guide: How This User Actually Works

## Core Frame

This user's operating logic centers on one conversion: turning ungrounded work into inspectable work before allowing execution to compound. He does not trust a plan, a fix, an abstraction, or a piece of copy until it has made contact with the real object — the actual codebase, the actual operator, the actual buyer's pain, the actual failure behavior. His signature move is a two-step loop: force a bounded discovery pass ("what is this, how is it structured, what constraints govern it"), then aggressively collapse whatever structure survives into the simplest form that still does the job. He is protecting against two failure modes simultaneously: acting on a false model of the system, and carrying complexity that outruns understanding.

What a generic reader would miss: his heavy up-front structuring is not process love, and his aggressive simplification is not minimalism as taste. Both are the same control mechanism pointed in different directions. Structure is added when ambiguity is high (checklisted codebase surveys, explicit evaluation criteria); structure is stripped when it stops earning its keep (config layers, factory patterns, defensive error handling, dense copy). The constant is legibility: work must stay understandable enough that he — or the non-technical operator, or the coding agent, or the buyer — can judge it directly. He is also not a planner by disposition. Once ambiguity is locally bounded, he switches to direct execution fast and treats further analysis as overhead.

## High-Leverage Signals

- **Inspection precedes judgment, always, when scope matters.** Before changing a codebase or adopting a pattern, he demands a structured inventory: project type, directory structure, build, tests, linting, style, existing rules. Recommendations must be earned by contact with the real system.
- **"Earn every layer" is his standing architecture rule.** He repeatedly cuts inherited engineering defaults — config factories, if-trees replaceable by types, redundant error handling already covered by a library, files that could be merged. Abstraction survives only if it buys clarity.
- **The real operator is the test of quality.** "Is this a good pattern for a non-technical person?" recurs. Work is judged against the actual person or agent who has to run it, not against elegance.
- **Corrections arrive as tighter specs, not complaints.** When output misses, he names the failure mode in one stroke (too broad, ungrounded, wrong layer) and rewrites the job with explicit boundaries, exclusions, and proof thresholds. He removes interpretive slack rather than negotiating.
- **Mid-task change triggers re-baselining, not adaptation of the old plan.** When assumptions shift, he restates the task as observable conditions, state transitions, and gating rules — what a new user sees first, what appears only when real data exists.
- **Speed is bought through reversible discovery, never through reduced certainty.** He moves fast in reconnaissance and scoped probes; once close to committing structure, correctness and maintainability outrank speed. He trades breadth, not verification.
- **Fixes require cause + smallest change + proof.** "It should work now" earns nothing. He wants the break point identified, the change bounded to the diagnosed cause, and a concrete before/after confirmation.
- **The recovery move under overload is compression.** When work sprawls or energy drops, he shrinks the problem to a bounded unit with an obvious completion test — a simpler config, a checklist, one visible decision — rather than pushing through with breadth.
- **Prompts themselves encode mode.** "Explore / decide / plan" signals planning-first; imperative verbs with embedded deliverables ("rewrite this to make more sense," "add these as leads, note the pain point") signal execution-now. He collapses decision-making into the prompt when ambiguity is already low.
- **Ordering violations are the fastest trust-killer.** Acting before inspecting, answering the second question before the first, producing output before the framing step — these create friction more reliably than difficulty or errors do.

## Salience Structure

- **First thing noticed: complexity that exceeds the job.** "This seems overly complex" fires early and reliably. Overbuilt structure registers as risk before it registers as sophistication.
- **Second: fit between artifact and actual operator.** Who has to use, maintain, or buy this — and can they? A pattern that works but is unusable by its real audience is flagged immediately.
- **Third: whether the answer is grounded in the real object.** Fluent output built on thin contact (broad matches instead of close reads, plausible fixes instead of diagnosed causes) reads as failure even when it sounds right.
- **Background until breakage: polish, completeness for its own sake, edge-case coverage.** He tolerates roughness ("good enough," "doesn't have to be perfect") as long as the core path is legible and verifiable.
- **Generic systems overweight:** thoroughness, formal process, defensive scaffolding, comprehensive answers. He treats these as drag unless bounded to operationally relevant facts.
- **Generic systems underweight:** the cost of hidden behavior. Indirection, invisible defaults, and clever routing are near-invisible to standard workflows but immediately salient to him.
- **Missing-state and precondition cases become signal fast in debugging** — what a new user should see, what fallback appears only when real data is absent. Happy-path fixes don't clear his bar.

## Lived Thresholds

- **Planning stops being useful the moment ambiguity is locally bounded.** Once there's a concrete candidate set and an obvious next step, further analysis reads as scope reopening. Verbs shift from "explore/decide" to "do."
- **Roughness is acceptable when the mode is exploratory or the deliverable is a draft** — he explicitly permits "rough," "good enough." It becomes unacceptable the moment the artifact will be operated, sold, or built upon.
- **Evidence is sufficient when the claim survives a challenge pass and the strongest support has been directly read** — not when coverage is exhaustive. He stops searching once the answer is earned; over-searching after that point is its own failure.
- **Abstraction crosses the line when he can no longer verify it quickly.** The test is not "is this flexible?" but "can I inspect the control surface?" When indirection wins, he collapses it (function store → hardcoded config file).
- **Uncertainty forces direct inspection when the change is structural or the environment is unfamiliar.** Reversible probes don't need this; anything that becomes backbone does.
- **A fix is trusted only past the diagnosis threshold:** cause identified, change scoped to that cause, confirming step run. Below that, it's speculation regardless of confidence.
- **Experiments are welcome while marked "for now" and reversible.** The threshold flips when a temporary arrangement starts hardening into permanent structure — then established, supported paths win.

## Breakdown and Repair

- **Trigger: plausible-but-ungrounded output.** Fluency outrunning verification, scope jumping from a few examples to a large claim. Repair: narrow the claim, demand direct passages/evidence, cut back rather than embellish.
- **Trigger: complexity creep in his own systems.** Repair: strip layers until the control surface is one obvious editable place — fewer files, fewer imports, explicit defaults, one execution path.
- **Trigger: the assistant using too much interpretive latitude.** Repair: rewrite the job as a stricter operating spec — what evidence to use, what to ignore, output shape, what not to mention, what counts as enough support. "Do it again under these constraints," not "try again."
- **Trigger: a fix that's structurally correct but behaviorally wrong.** Repair: keep narrowing the logic into explicit conditions and gating rules; rewrite acceptance conditions against current-vs-intended behavior.
- **Trigger: fix churn without understanding.** Repair: stop the loop entirely and demand the problem be explained fully before the next attempt.
- **Trigger: ordering inversion** — output before inspection, second question before first. Repair: sequence protection, restated by hand ("look first," "answer this one first," "decide and plan first").
- **Trigger: sprawl under load.** Repair: convert diffuse work into a bounded unit with a visible completion test; regain traction through a smaller inspectable artifact, not more ideas.

## Quality Detection

- **Proof = decision-readiness.** Strong work makes the next move obvious: a summary an agent can execute from, copy a buyer immediately recognizes, a config a maintainer can read directly.
- **He treats explanation-plus-verification as the trust currency for fixes** — cause named, smallest change, before/after confirmation tied to the original failure.
- **Distrusted: fluent prose that hides its basis.** Citations-as-decoration, invented frameworks, research exhaust, tooling chatter — all read as performative rigor, not evidence.
- **Distrusted: completeness without operational relevance.** Comprehensive is good only when bounded to facts needed to act.
- **Shallow = technically valid but operationally expensive:** awkward copy that requires interpretation, a repo summary that names the project but not how to work in it, architecture that solves a problem the task doesn't have.
- **Overprocessed = structure doing more than the job requires:** unnecessary configurability, defensive checks duplicating library behavior, meta-context or process scaffolding leaking into final artifacts.
- **High quality does two things at once: covers the relevant ground AND simplifies.** He asks for tightening and completeness in the same breath — detail organized so someone can act, not detail as evidence of effort.

## Artifact Relation

- **The artifact is the source of truth; descriptions of it are suspect.** He forces reads of the actual component, schema, config, or repo before permitting judgment. "Read that," not "recall that."
- **He uses concrete inventories as thinking surfaces:** checklists of project type / build / tests / style are how he loads an unfamiliar system into a judgeable form.
- **The artifact is his abstraction-drift detector.** When a design starts to feel clever, he tests it against the real file, the real operator, the real library behavior — and the abstraction usually loses.
- **Logs and reproductions are debugging surfaces he explicitly requests** — change the command to emit a usable log file, manually test the tool to see what it actually does versus what it promises.
- **Structured deliverables are coordination objects:** the executable brief or complete spec is how he hands work to agents — self-contained enough that no strategic clarification is needed downstream.
- **A smaller concrete artifact is his traction-recovery device.** When momentum drops, he produces or demands a reviewable intermediate object (simpler config, scoped summary, first-pass decision) as proof the work is controllable again.
- **Final artifacts must not expose their scaffolding.** He strips references to prior interactions, process, and generation context; the output has to stand on its own.

## Mode Shifts

- **Exploration → planning:** triggered by unfamiliarity or architectural weight. Exploration is checklisted, not open-ended — bounded reconnaissance with named dimensions, ending in a comprehensive-but-scoped summary.
- **Planning → execution:** triggered by ambiguity becoming locally bounded — concrete candidate set, obvious next step, sufficient evidence. At that point he treats further analysis as scope reopening and issues direct imperatives.
- **Execution → re-baselining:** triggered by any assumption shift or behavioral surprise. He stops optimizing the old plan and rewrites acceptance conditions from current reality.
- **Execution → diagnosis:** triggered by "looks right but behaves wrong." Standards escalate sharply: cause-level explanation and confirming steps become mandatory before continuing.
- **Any mode → simplification:** triggered by structure exceeding need. This can interrupt agreed-upon designs mid-implementation — he reopens settled decisions when hidden maintenance cost appears.
- **Diagnosis → halt:** triggered by fix churn. He suspends the repair loop and demands full explanation before allowing another attempt.
- **Standards change across modes:** exploration tolerates roughness and speed; commitment points demand durability (e.g., preferring a robust two-key state pattern over a merely working one); handoff demands complete, self-contained specs.

## Success Conditions

- Good execution inspects before acting, and shows its inspection — the answer maps back to the requested dimensions rather than hiding in fluent prose.
- Good execution keeps changes small, diagnosed, and verified: cause, minimal fix, concrete confirmation, no silent collateral change.
- Good execution matches the local system: existing conventions, existing library guarantees, the way the rest of the project already does it.
- Good execution produces artifacts the real operator can use without interpretation — and strips process residue out of the final form.
- Good execution stops when the answer is earned; it does not keep expanding search or adding coverage after sufficiency.
- Weak execution invents frameworks, elaborates beyond the ask, answers the wrong layer, or extends scope the user did not open.
- Weak execution ships plausible fixes without diagnosis, or adds structure (files, layers, safeguards) that the task never justified.
- Weak execution inverts sequence — producing output before loading context, or answering the exciting part before the first requested part.

## Tensions and Tradeoffs

- **Comprehensiveness vs. compression.** He asks for "comprehensive summaries" and demands simplification — resolved by bounding thoroughness to operationally relevant facts. An agent that reads only one side of this will fail.
- **Fast execution vs. earned execution.** He wants direct action once scope is clear, but the right to act must be earned by inspection first. Speed applied before grounding reads as recklessness; grounding applied after clarity reads as stalling.
- **Simplification vs. proper fixes.** He strips defensive scaffolding, yet rejects minimal-compliance patches and demands durable, correct fixes. Cutting ceremony ≠ cutting rigor.
- **Delegation vs. retained judgment.** He gives agents real autonomy inside bounded operations but keeps framing, proof standards, and final synthesis centralized. Vision is non-negotiable; execution is fully delegable via complete specs.
- **Reopening decisions vs. momentum.** He will reopen agreed designs when hidden cost appears — which looks like indecision but is actually a reversibility discipline. Once checks clear, he commits fast.
- **Structure as cure and structure as disease.** He adds explicit structure to tame ambiguity and removes structure to restore legibility. The variable is whether structure increases or decreases inspectability at that moment.
- **Pragmatic abandonment vs. repair.** When infrastructure is irreparably tangled (broken dependencies), he abandons the path and reroutes toward what unlocks the next concrete value, rather than sinking effort into repair.

## Boundary Conditions

- **Strongest:** codebase exploration, architecture and config decisions, debugging, prompt/system design, workflow automation, and revenue-facing execution (leads, positioning, copy tightening). All the core patterns fire here.
- **Relaxed:** simple factual lookups and quick troubleshooting — direct one-line questions, no imposed structure, no discovery pass.
- **Relaxed further in exploratory/creative discussion:** he explicitly permits approximation and speculation ("rough," "good enough") when the mode is brainstorming rather than actionable precision. The auditable-scope rule is context-dependent.
- **Mixed evidence on non-technical domains:** the inspection-first, simplify-second discipline is well-documented in technical and revision-heavy work; whether it carries at full strength into all business or interpersonal tasks is less supported.
- **The constraint-driven fluency requires anchors:** his rigor is strongest with concrete artifacts (code, configs, metrics, real leads). In unanchored philosophical territory, the verification loops largely switch off.
- **Thoroughness requests exist but are bounded:** when he asks for "comprehensive," treat it as "complete map of what matters for the decision," not open-ended coverage.

## Counterpart Implications

- **Because he earns action through inspection, a fitting counterpart does reconnaissance unprompted and shows its map before proposing changes** — arriving with "here is what this actually is" rather than "here is what I'd do."
- **Because his corrections are spec-tightening, a fitting counterpart treats every correction as a durable constraint, not a one-off preference** — internalizing "no invented frameworks, no scope extension, no process residue" as standing rules.
- **Because he trusts diagnosed fixes, a fitting counterpart always ships cause + smallest change + verification together** — never a confident patch alone. Proof style: concrete before/after, not assurance.
- **Because he polices ceremony, intelligent pushback looks like "this layer isn't earning its cost" or "the library already handles this"** — simplification challenges land well; procedural or completeness challenges land as bureaucracy.
- **Because he collapses decision-making into concrete prompts, a fitting counterpart reads verb signals accurately:** "explore/decide/plan" means map first; imperative-with-deliverable means execute now without reopening scope.
- **Because he recovers via compression, a fitting counterpart responds to drift by shrinking the work into a bounded, checkable unit** — a smaller artifact, a restated claim, a scoped next step — rather than by adding effort or breadth.
- **Because sequence violations kill trust, a fitting counterpart visibly completes step one before touching step two** — and never lets the interesting part of a task jump the queue.
- **Because his vision is retained and execution delegated, the natural partnership shape is: he frames, the counterpart executes completely from the spec, clarification questions are welcome, strategic co-authoring is not.** The presence that fits is a rigorous executor who makes complexity visible and never performs rigor it doesn't have.

## Open Questions

- How much of the planning-first discipline holds under hard deadlines versus the evidence's mostly self-paced work? One trace suggests scope collapses to rough deliverables when time windows narrow — how far does that extend?
- Does the inspection-first standard apply to non-software domains (finance, hiring, personal decisions), or is it artifact-dependent?
- The delegation model shows "complete spec, no strategic co-creation" — is this a stable preference or an adaptation to current tooling limits?
- His verification demand varies (formal tests vs. lighter manual checks). What actually determines which proof level a given fix requires?
- One trace suggests a gap between intellectual processing and externally validated output (action delay). How much does this shape day-to-day work versus being an occasional pattern?
- When he permits speculation in exploratory contexts, is there a signal marking the boundary back to rigor, or must the counterpart infer the mode shift?

## Evidence Fragments

**High-Leverage Signals**
- "Explore this codebase: project type, directory structure, build system, testing setup, linting, code style, existing rules — then a comprehensive summary."
- "This seems overly complex — can it just be a hardcoded config file instead of a function store?"
- "Is this a good pattern for a non-technical person?"
- "Don't guess." / "Read that." / "Just answer, be concise."

**Breakdown and Repair**
- Fix churn halted: explain the problem fully before the next loop.
- Rewrote a broken flow as explicit conditions: what a new user sees first, what appears only after a status exists, what fallback shows only when real data is absent.
- "Rewrite this to make more sense" — clarity correction, not polish.
- Post-change audit: "Was that change even needed? What risks did it introduce?"

**Quality Detection / Artifact Relation**
- Rejected redundant error handling because the underlying library already covers it.
- Asked whether type information could replace an if-tree in a factory.
- Demanded repo summaries include build/lint/test/style rules "so an agent can actually work in it."
- Stripped references to prior interactions from final prompts — output must stand alone.

**Thresholds / Mode Shifts**
- "For now" / "later" markers on experimental architecture — reversible until it becomes backbone.
- Direct execution prompts embed target, action, and acceptance: "search small B2B firms in [place], add as leads, note the biggest pain point AI could solve."
- Explicit permission for roughness in exploratory mode: "rough," "good enough," "doesn't have to be perfect."
- Priority logic under pressure: pick the path that "unlocks the next amount of money" and bypasses tangled dependencies rather than repairing them.
