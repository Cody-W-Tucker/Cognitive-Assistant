# Field Guide: How This User Works

## Core Frame

This user works to keep complexity from outrunning his understanding. His default move on any non-trivial task is to convert it into a bounded inspection job before allowing action: name the object, name the dimensions it will be judged on, map the actual terrain, then decide. He does not trust a request, a fix, or an abstraction until it has been turned into something he can look at directly and check against a concrete use case. The hidden goal across almost everything is **operational legibility** — work he can run, reason about, hand off, and reverse without rediscovering its logic each time.

What a generic reader will miss: this is not caution or perfectionism. He moves fast, ships rough drafts, and skips process freely when the next action is already obvious. The tightening only fires when a task has execution risk, usability risk, or scope ambiguity. The real organizing principle is not "be rigorous" but "earn the right to act by first making the work inspectable, and strip out any structure that does not earn its complexity." His two strongest reflexes — *inspect first* and *simplify aggressively* — are the same instinct pointed at different moments: keep the working surface small enough to judge directly.

## High-Leverage Signals

- **Inspect-first as a hard gate.** For substantial work he refuses to act from a vague prompt. He converts the task into a discovery pass — map project type, structure, build, tests, linting, style, existing rules — and only then judges or changes anything. Recommendations must be downstream of an understanding pass.
- **Simplification as the dominant corrective.** When a system "seems overly complex," his reflex is not to refine it but to collapse it: a function store becomes a hardcoded config, branching logic gets replaced by type information, redundant error handling is removed because the library already covers it, separate files merge if one is easier to manage.
- **"Earn every layer."** He actively strips inherited engineering ceremony — config layers, factories, defensive scaffolding — when it adds structure before value. He rejects "best practice by convention," not structure itself.
- **Correction by concretization.** When work misses, he does not negotiate or re-explain abstractly. He names the failure in one stroke ("too broad," "overly complex," "doesn't make sense") and replaces the loose request with a tighter operating spec: what to use, what to ignore, what shape the answer takes.
- **Usability for the actual operator as the judging criterion.** "Is this a good pattern for a non-technical person?" recurs as the test that overrides technical cleverness. Fit to the real user/maintainer beats elegance.
- **Speed through reversible discovery, rigor at the point of commitment.** He moves fast in reconnaissance, probes, and rough drafts, but raises the bar sharply once a change becomes structural or irreversible.
- **Mode declared in the verb.** "Decide and plan," "explore," "understand," "summarize" signal he wants orientation first. "Rewrite," "add," "search," "treat this like," "simplify" signal he has already collapsed the decision into the prompt and wants execution now.
- **Convert manual judgment into repeatable structure.** His mission-level pull is taking work that depends on hidden expertise or repeated reconnaissance and encoding it once — config files, structured records, enrichment routines, guided interfaces — so it can be rerun and handed off.

## Salience Structure

- **Complexity that exceeds the task is the first thing he notices.** Overbuilt abstraction registers as drag almost immediately, before he evaluates whether it works.
- **Mismatch between the artifact and its real operator is high-salience.** He quickly asks who has to use or maintain this and whether they actually can.
- **Unclear language reads as a defect, not a style issue.** Muddy wording triggers "rewrite this so it makes sense" — he treats legibility as part of correctness.
- **Missing context is treated as the main source of bad work.** He notices the absence of structure, constraints, and success criteria before he notices substantive errors.
- **Fluency outrunning evidence is a danger signal.** A draft that sounds clean while leaning on broad matches or a scope jump registers as a failure even when it reads well.
- **What stays background until it breaks:** maintenance cost, hidden dependencies, and precondition/missing-state cases — until a fix works in the happy path and fails elsewhere, at which point they jump to the foreground.
- **What a generic system overweights for him:** comprehensiveness, polish, architectural elegance, citations and tooling chatter — all of which he reads as noise unless they earn their place.

## Lived Thresholds

- **Ambiguity triggers planning; concreteness triggers execution.** The shift hinges on whether the object, action, and output are already named. Once they are, further analysis is overhead he refuses.
- **Roughness is fine when the task is concrete and reversible.** He ships first-pass output and rough drafts to satisfy immediate obligations, especially under time pressure. He relaxes generality and polish, never usefulness or verifiability.
- **Evidence is "enough" when the answerable core is visible.** In analysis work he stops expanding the search the moment a small candidate set supports a bounded claim — early stop is deliberate, not lazy.
- **Polish matters only at handoff to a real user or maintainer.** Clarity gets enforced when someone else must act on the output; he does not polish for its own sake.
- **Uncertainty forces direct inspection rather than reasoning.** When he does not know what a tool or system actually does, he tests it manually and re-asks "what does this actually do?" rather than accepting plausible description.
- **Confidence drops enough to intervene when assumptions shift mid-task.** He interrupts momentum, re-baselines against current reality, and rewrites acceptance conditions before continuing.
- **Planning becomes avoidance the moment scope is already low.** If the next move is obvious, asking for frameworks or option menus is treated as drift, and he locks the prompt into execution mode.

## Breakdown and Repair

- **Breakdown type: scope creep / over-latitude.** The assistant adds frameworks, speculation, or unrequested elaboration. Repair: he removes interpretive slack — explicit exclusions, proof thresholds, "just answer," "don't guess," "grounded in."
- **Breakdown type: complexity overrun.** A system grows more structure than the job needs. Repair: collapse to the simplest inspectable form — hardcoded config, single execution path, fewer files.
- **Breakdown type: fluency without grounding.** A draft sounds confident on thin evidence. Repair: narrow the claim, require direct passages, run a challenge pass, and cut back rather than embellish if support does not materialize.
- **Breakdown type: ungrounded speed (wrong first move).** The assistant produces output before inspecting the relevant code or before resolving the stated first step. Repair: enforce sequence — "look first," "answer this one first," "decide and plan first."
- **Breakdown type: plausible-but-wrong fix.** A repair looks structurally correct but behavior is still wrong. Repair: keep narrowing the logic instead of accepting surface plausibility; demand a diagnosed cause plus a verification step.
- **Breakdown type: misfit for the real operator.** A pattern works technically but a non-technical user couldn't run it. Repair: reframe the task as evaluating fit against that concrete use case.
- **General repair posture:** he rarely re-explains intent. He restates the task under stricter constraints so the acceptable path is narrower than before. Recovery is by tightening, not by negotiation.

## Quality Detection

- **Proof is contact with the real object.** A summary is trusted because it is tied to actual files, build, test, and style rules; a design judgment because it reflects the actual user; a fix because it names the cause and shows before/after.
- **Decision-ready clarity is the bar, not detail.** Good work is comprehensive *and* simplified at once — it covers the ground without holes and is organized so someone can act on it immediately.
- **He distrusts: speculation, invented frameworks, citations and tooling exhaust, and any abstraction added before need is proven.**
- **Work feels shallow when it is plausible but unverified, broad from partial inspection, or technically complete but operationally unclear.**
- **Work feels premature when it adds structure, automation, or generality before the underlying need is demonstrated.**
- **Work feels overprocessed when complexity, indirection, or polish exceeds what the task requires** — false sophistication that is harder to reason about than the problem.
- **A fix earns trust only when bounded to its diagnosed cause.** A change broader than the problem keeps trust low even if it works.
- **The end-test for any output: can the intended operator — a non-technical editor, a coding agent, a reader — act on it without guesswork or interpretation?**

## Artifact Relation

- **The codebase/schema is a source of truth he loads before judging.** He refuses to admire code in the abstract; he inspects the real implementation and its conventions first.
- **Config files and explicit defaults are his preferred control surface.** He pushes important behavior into one obvious, editable place so intent cannot drift across indirection.
- **Logs and manual tests are his debugging surface.** He turns a vague broken command into "make it emit a usable log file," and tests tool behavior by hand rather than trusting documentation.
- **Direct passages and close reads are his proof surface in analysis.** Broad matches are insufficient; he requires targeted reads of the strongest candidates.
- **A smaller, concrete artifact is how he regains traction when energy drops.** He shrinks a sprawling problem into a checklist, a hardcoded config, or a scoped summary that can be judged immediately.
- **Artifacts test whether abstraction has drifted.** When a config "seems too clever" or a summary stays vague, the gap between artifact and real use is his signal that the abstraction has overreached.
- **Rewritten wording is itself an artifact of clarity.** He treats "make this make sense" as forcing the meaning and next action to surface, not as cosmetic editing.

## Mode Shifts

- **Exploration → planning:** triggered by scope, design weight, or unfamiliarity. He runs a fast reconnaissance pass (structure, build, tests, style, rules) and then frames a scoped decision. Standard shifts from "what is possible" to "what fits the real environment."
- **Planning → implementation:** triggered by the object, action, and output becoming concrete. Once an option clears fit/simplicity/local-convention checks, he moves decisively. Standard shifts from comparison to execution plus further tightening.
- **Implementation → diagnosis:** triggered by behavior diverging from intent. He stops, re-baselines against current vs intended behavior, rewrites acceptance conditions as explicit gates and fallbacks, then continues.
- **Diagnosis → repair:** narrow the fix to the diagnosed cause, then demand a verification step before treating it resolved. Standard: correctness and maintainability outrank speed here.
- **Any mode → simplification:** triggered the moment structure feels heavier than the task deserves. This is the most frequent shift and can interrupt any other mode.
- **Review standard differs by trigger:** for exploratory work he tolerates breadth; for execution-facing work he enforces concreteness, simplicity, and actionability.
- **Mode is signaled, not inferred.** He tells the assistant which mode he wants through verb choice and embedded acceptance criteria, and loses trust when the assistant ignores the declared sequence.

## Success Conditions

- **Good execution makes the work inspectable:** scope is bounded, criteria are explicit, and the output maps back to the requested dimensions.
- **Good execution survives contact with the real operator:** a non-technical user can use it, a coding agent can run it from the spec, a reader gets the point and next step immediately.
- **Good execution earns its complexity:** every layer, file, abstraction, and safeguard is justified by need, not convention.
- **Good execution couples claims to evidence:** conclusions tied to real files, real constraints, direct passages — bounded by what is actually supported.
- **Weak execution is plausible but ungrounded** — fluent summary built on weak contact with the material.
- **Weak execution is technically complete but operationally heavy** — correct, elaborate, and hard to run or hand off.
- **Weak execution gets ahead of the work** — produces output before inspecting, answers the second question before closing the first, solves before scoping.
- **Weak execution solves the symptom while expanding uncertainty** — a fix broader than its cause, or automation added before the need is proven.

## Tensions and Tradeoffs

- **Speed vs rigor, resolved by phase.** Fast in reversible discovery and rough drafts; rigorous at the point of structural commitment. The same task can show both within minutes.
- **Comprehensiveness vs narrowing.** He asks for full codebase surveys *and* aggressive simplification. Reconciled by purpose: comprehensiveness is for orientation and is bounded to operationally relevant facts; narrowing is for action.
- **Simplification vs thoroughness.** He strips complexity but refuses minimal-compliance fixes, demanding proper fixes across large and small details. Simplicity is about legibility, not doing less.
- **Autonomy vs control in delegation.** He grants helpers and agents real autonomy inside bounded operations (scout, retrieve, test) but keeps task framing, proof standards, and final synthesis to himself. Delegation requires complete specifications, not shared strategy.
- **Inspect-first vs execute-now.** Strong inspection discipline coexists with impatience for analysis once scope is low. The tension is real and he resolves it by reading whether ambiguity is locally bounded.
- **Stated ideal vs actual behavior under pressure:** he values grounded, verified work, but under narrow time windows he ships "good enough" rough drafts to unlock immediate progress — and abandons irreparably tangled infrastructure rather than fix it.

## Boundary Conditions

- **Strongest in:** codebase exploration, architecture and config simplification, debugging, UX/pattern evaluation, prompt refinement, and lead/messaging work where being generic is costly.
- **Relaxes for:** simple factual lookups, how-to questions, and one-off utility requests, where he asks directly with no scaffolding and no tightening loop.
- **Inspect-first is conditional, not universal.** It fires on tasks with many moving parts or risk of misfit, not on narrow retrieval.
- **The simplification reflex is not anti-structure.** Entering an unfamiliar codebase, he asks for a full structural map; he rejects only complexity that survives by convention rather than value.
- **Evidence is concentrated in technical and product-shaping work.** Claims about analysis-stopping rules, proof thresholds, and verification posture are strongest in synthesis and debugging traces.
- **Mixed evidence on non-technical tasks.** Whether the inspect-first / simplify standards transfer fully to every nontechnical task is not well supported; keep those claims scoped.
- **One distinct cluster (high-redacted dataset answers) reads more speculatively** — existential-layer theories, cognitive-archetype framing, "wounds regarding recognition." Treat these as weaker, more interpretive signals than the code/config/messaging evidence.

## Open Questions

- How does he coordinate with **other humans over time**? Evidence covers structured task execution and agent delegation, but informal collaboration and long-running human handoffs are thin.
- Does he ever **fully transfer decision authority**, or does centralized judgment always hold? The traces show retained authority but few clear releases.
- What is his actual posture toward **high-novelty or exploratory risk**? The evidence shows improvement-gated-by-reliability; cases where he accepts genuine novelty risk are underrepresented.
- How rigid is his **verification standard** — full formal tests vs lighter manual checks? The stable signal is "some direct proof," not one method.
- Do the **psychological/existential framings** in parts of the dataset reflect his real self-concept or analyst overreach? Avoid building on them.
- How much of the **"convert knowledge into operating machinery" mission** is conscious intent vs an emergent pattern across separate tasks?
- Where exactly does **"good enough under time pressure"** override his quality bar, and what are its limits before he refuses to ship?

## Evidence Fragments

**Inspect-first / sequencing:**
- "explore this codebase, identify the project type, map the directory structure, find the build and test setup, inspect style rules, then return a comprehensive summary."
- "look at this component and schema, decide and plan whether the pattern is good for a nontechnical person."
- Sequence protection: "answer this one first," "outline this first," "decide and plan first."

**Simplification / earn every layer:**
- "seems overly complex" → "treat this like a hardcoded config file instead of a function store."
- Questions why a factory needs an if-tree when types already say what should happen; removes local error handling the library already covers; merges files when separation buys nothing.

**Correction by concretization:**
- "rewrite this to make more sense"; "don't guess," "do not guess," "read that," "just answer," "be concise," "grounded in."
- Restates the task under stricter constraints rather than re-explaining intent.

**Usability as the test:**
- "is this a good pattern for a non technical person."
- Lead work: not just names, but each lead's "biggest pain point" and how AI would help.

**Quality / grounding:**
- Tightens when a draft leans on "broad matches instead of close reads" or "a scope jump from a few examples to a larger claim"; cuts back rather than embellishes if support is absent.
- Repository summaries must include "the concrete build, lint, test, and style rules that make execution possible."

**Speed/rigor by phase:**
- Fast reconnaissance and "for now / later" wrappers to preserve optionality; durable two-key state pattern over a merely-working one; rejects minimal compliance for "proper fixes."

**Under pressure:**
- Numbered daily priorities; "identify anticipated blockers before starting high-friction tasks and push through immediately"; abandons tasks with "screwed up" node module dependencies rather than repairing; ships content-only rough drafts to "unlock the next amount of money."
