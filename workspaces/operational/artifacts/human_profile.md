# Field Guide to How This User Works

## Core Frame

This user works to keep execution honest by forcing contact with the real object before committing to action. The recurring move across every domain — code, config, copy, lead generation, agent design — is the same: name the thing, inspect it, bound the decision, then act. He is trying to secure *operational legibility*: a state where the structure, the constraints, the intended operator, and the success criteria are all explicit enough that a decision can be inspected rather than trusted on faith. What he is most consistently avoiding is **false progress** — output that is fluent, elaborate, or technically correct but operationally useless, hard to verify, or mismatched to whoever has to use it.

A generic reader will likely read this as "careful, process-oriented engineer" and overweight the planning. That misses two things. First, the planning is not a ritual; it is a *control surface* he installs only when ambiguity or scope makes premature action dangerous, and he drops it instantly for narrow tasks. Second, his deepest instinct under pressure is not to add rigor but to **simplify** — to strip moving parts until the control surface is small enough to judge directly. The orientation pass and the simplification pass are the same impulse pointed at two ends of a task: understand reality first, then reduce it to the smallest legible form that still does the job.

## High-Leverage Signals

- **Inspect-before-prescribe is the default for consequential work.** He opens substantial tasks by mapping the terrain (project type, structure, build, tests, linting, style, existing rules) rather than asking for a solution. Action is something the situation has to *earn* through being understood.
- **Correction by concretization.** When something misses, he doesn't negotiate or re-describe his dissatisfaction. He names the failure mode in one stroke and replaces the loose request with a tighter operating spec: what evidence to use, what to ignore, what shape the answer takes, what not to mention.
- **"Earn every layer" toward complexity.** He actively strips inherited engineering defaults — config layers, factories, type-check branching, redundant error handling — asking why each cannot collapse. Standards survive only if they materially improve clarity or control, not because they're conventional.
- **Simplification is his primary recovery behavior.** Under load, drift, or sprawl, he reduces scope, hardcodes, compresses language, and demands the next step be obvious. He recovers through *constraint, not expansion*.
- **Usability-for-the-real-operator as a hard filter.** "Is this a good pattern for a non-technical person?" recurs as a gate before adoption. Output is judged against the actual user (a non-technical editor, a coding agent, a buyer reading copy), not against abstract correctness.
- **Fast discovery, high-integrity execution.** He accepts speed in reconnaissance and debugging probes but raises the bar sharply at the commit point — preferring durable fixes over "looks right" patches, rejecting minimal compliance.
- **Bug reports arrive pre-bounded.** He packages failures as observable mismatches (where, what's failing, reproducible context) rather than vague complaints, and trusts a fix only when it's coupled to a diagnosed cause plus a verification step.
- **Delegation with centralized judgment.** He gives agents and helpers bounded operations — scout, retrieve, test — but keeps task framing, proof thresholds, and final synthesis under direct control. Authority over direction is non-negotiable; execution is delegated through explicit specs.

## Salience Structure

- **Mismatch with the real operator becomes signal fast.** Before almost anything else, he checks whether the thing fits the person who'll use it. A clever pattern that a non-technical user can't operate registers as a defect immediately.
- **Unjustified complexity jumps out.** A config that "seems overly complex," an abstraction layer, a function store where a flat file would do — these are noticed early and treated as drag, not sophistication.
- **Ungrounded fluency triggers suspicion.** Output that sounds clean while leaning on thin evidence, broad matches instead of close reads, or a scope jump from few examples to a large claim reads as a failure forming.
- **Background until it breaks: polish, elegance, completeness.** He doesn't notice missing polish; he notices missing *legibility*. Exhaustive coverage stays in the background unless it's the kind of completeness that means "enough context to act."
- **Generic systems overweight thoroughness and underweight fit.** A generic assistant assumes more detail is better. This user reads detail that isn't decision-relevant as noise, and reads a missing build/test/lint/style summary as a real gap.
- **Process exhaust is noise to be stripped.** Citations, file/line references, tool chatter, references to prior or future conversations — these read as clutter that distracts from judgment, and he removes them.

## Lived Thresholds

- **Planning turns on at ambiguity + scope + misfit risk.** When a task has architectural, usability, or repository-wide consequences, he forces orientation first. For narrow, specified tasks ("rewrite this," "add these leads," "change this command"), planning would be overhead and he skips straight to execution.
- **Roughness is fine while the move is reversible.** Sketchy setups, temporary UI, wrappers, "for now / later" scaffolding are all acceptable during exploration. Roughness stops being acceptable the moment a choice becomes structural — core config, infrastructure, repeated workflows, operator-facing interfaces.
- **Evidence is enough when the answerable core is visible.** He stops expanding the search once a small candidate set supports the claim and the next move is obvious. He then harvests only the highest-yield reads and finalizes — early stopping is deliberate, not impatience.
- **Polish matters only at handoff.** Wording gets tightened when someone else must follow it, execute it, or be persuaded by it. The standard is "easier to act on," never elegance for its own sake.
- **Uncertainty forces direct inspection.** When he can't trust a first-pass interpretation, he won't reason about it abstractly — he reads the actual code, tests the actual tool behavior, surveys the actual repo. The unknown gets converted into a bounded inspection job.
- **Confidence drops → re-baseline.** When assumptions shift mid-task, he stops optimizing the old plan and restates the work as observable conditions, state transitions, and gating rules before continuing.

## Breakdown and Repair

- **Failure type: scope/rigor/framing drift.** When a response is too broad, ungrounded, or answers the wrong layer, he repairs by *removing interpretive slack* — restating the task with explicit boundaries, exclusions, and proof thresholds, then asking again under stricter constraints. Not "try again" but "do it again, narrower."
- **Failure type: overbuilt structure.** When a system has accreted ceremony, he repairs by collapsing it — hardcode the config, remove the redundant error handling the library already covers, combine files, kill the branching the type system makes unnecessary.
- **Failure type: muddy language.** When wording doesn't "make sense," he doesn't ask for flair; he asks for clarity and a more obvious next action, often rewriting himself toward simpler form.
- **Failure type: ungrounded fluency.** When a draft leans on weak signals, he narrows it, requires direct passages, runs a challenge pass against the weakest cases, and *cuts the claim back* rather than embellishing if support doesn't materialize.
- **Failure type: order inversion.** He loses trust when the assistant acts before inspecting, expands before framing, or answers the exciting second question before closing the first. Repair is sequence enforcement: "look first," "answer this one first," "decide and plan first."
- **Failure type: blind patch.** A fix asserted without a diagnosed cause stays low-trust. Repair is demanding cause-level explanation plus a concrete before/after verification tied to the original failure.
- **General repair grammar: tighten, don't broaden.** Across all breakdowns, recovery means reducing surface area — narrower scope, fewer parts, harder proof — never adding more output to rescue a drifting task.

## Quality Detection

- **Proof = contact with the real object.** A summary is trustworthy because it's tied to actual files, build commands, and constraints. A design judgment is trustworthy because it reflects the actual operator. Abstract confidence doesn't count.
- **Quality = decision-ready clarity, not detail.** Good work makes the important structure easy to understand, covers the relevant ground without obvious holes, *and* stays anchored to the real use case — all three at once. Detail alone reads as elaborate but weak.
- **He distrusts: speculation, invented frameworks, unsolicited abstraction, scope creep.** "Don't guess," "just answer," "be concise," "grounded in" recur as enforcement against probabilistic intent-modeling.
- **Shallow tell:** plausible-but-unverifiable, can't drive the next action, requires interpretation before it communicates.
- **Premature tell:** abstraction added before need is proven, automation introduced too early, moving parts harder to reason about than the original problem.
- **Overprocessed tell:** citations, tool chatter, performative rigor, multi-voice or flowery output, structure that's bureaucratic rather than legible.
- **The honesty standard:** he prefers answers that separate observation from inference and state their own limits — work that "feels earned rather than merely fluent."

## Artifact Relation

- **The artifact is the source of truth.** He returns to the actual codebase, schema, component, config, or tool behavior rather than reasoning from a remembered template. "Read that" is a recurring correction.
- **The artifact is a drift test.** When abstraction starts feeling clever, he checks it against the concrete thing it has to serve — can a non-technical person actually use this pattern? Does the function store need to be more than a config file?
- **Direct testing beats assumed behavior.** With tools, he manually tests, notices the tool isn't doing what he assumed, and narrows the question from "how do I use this?" to "what does this actually do, and what would I need instead?"
- **Logs and tests are demanded as observable evidence.** He'll ask a broken command to emit a usable log file rather than debug abstractly; he wants a confirming reproduction or before/after result before trusting a fix.
- **A smaller artifact restores momentum.** When energy drops, he shrinks the problem to something inspectable — a hardcoded config, a scoped checklist, a concrete inventory — because a crisp intermediate object proves the work is now controllable.
- **Structured specs are his coordination object.** He hands off through complete, self-contained executable briefs that transfer execution without needing further clarification — the artifact carries the intent so collaboration doesn't require shared strategy authorship.

## Mode Shifts

- **Exploration → planning:** triggered by ambiguity, scope, or misfit risk. Verbs flip to *look, decide, plan, explore, understand, summarize*. Standard becomes "map the terrain well enough to judge fit and constraints."
- **Planning → implementation:** triggered by an option clearing three checks — fits real use, matches local conventions, removes avoidable complexity. Once cleared, he moves fast from comparison to execution and further tightening.
- **Implementation → diagnosis:** triggered by behavior diverging from intent. He pauses, re-baselines into observable conditions and gating rules, and tightens logic instead of accepting surface plausibility.
- **Direct execution mode:** triggered when the prompt already contains target + action + output format. Verbs flip to *rewrite, add, search, note, make, treat this like*. Further analysis is now overhead; re-opening scope is the failure.
- **Review/refinement:** standard shifts from "does it work" to "is it legible, usable, and minimal." Here he strips layers, compresses language, and rejects minimal compliance in favor of proper fixes.
- **The governing rule across shifts:** he earns the right to act by loading the right context first, then refuses to re-open scope once the next move is obvious. Both halves are load-bearing.

## Success Conditions

- **Good execution converts a messy domain into a usable operating system** — a structured workflow, a simpler config, a guided interface, a lead annotated with its concrete pain point. Knowledge gets out of heads and chat threads into reusable, runnable form.
- **Good execution is reversible until enough real context is visible**, then becomes a bounded, defensible commitment with visible consequences.
- **Good execution stays small enough to judge.** It reduces moving parts, preserves what can be inspected, and makes the next action obvious.
- **Weak execution is fluent but ungrounded** — persuasive summary on weak contact with the material, scope expanding faster than evidence, structure substituting for judgment.
- **Weak execution is overbuilt** — abstraction, configurability, or defensive scaffolding that adds ceremony before value and is harder to operate than the problem requires.
- **Weak execution leaks process** — exposes seams, tool chatter, or meta-context that forces downstream humans to adapt to the assistant's logic.
- **Weak execution solves the happy path only** — works in the demo, fails on missing-state, precondition, or the real operator's actual level of use.

## Tensions and Tradeoffs

- **Thoroughness vs. tightening.** He asks for *comprehensive* codebase summaries yet relentlessly *strips* complexity. Resolved by scope: completeness means "all the facts needed to act," never open-ended exhaustiveness.
- **Speed vs. correctness.** He moves fast — but only through reversible discovery. He trades speed against *breadth*, never against verifiability. Fast reconnaissance buys safe speed; the commit point pays full rigor.
- **Autonomy vs. control.** He delegates real operations to agents and helpers but never delegates the standard of proof or the framing. Collaborators are instruments for narrowing uncertainty, not co-authors of the answer standard.
- **Simplicity vs. structure.** He rejects conventional structure that survives only by convention, yet adopts standard engineering scaffolds (MVP, small diffs, post-change checks) readily when they keep work small and testable. The line is "does this layer earn its keep."
- **Inspection vs. momentum.** Front-loaded orientation can read as slow, but it's what lets him move fast later without rework. The risk is that orientation tips into avoidance — though the traces show him stopping the survey the moment the answerable core appears.
- **Technical fluency vs. action-delay.** A noted vulnerability: high comfort in abstract/conceptual processing can stall the externally-validatable deliverable. His own simplification instinct is the counterweight, but insight that isn't immediately paired with executable structure is a live failure mode.

## Boundary Conditions

- **Strongest in:** technical implementation, debugging, codebase exploration, architecture/config simplification, UX-for-non-technical-users judgment, prompt refinement, lead qualification and sales-copy tightening.
- **Relaxes for:** simple factual lookups, one-off how-to questions, quick troubleshooting — here he often asks direct one-line questions with no scaffolding, no inspection pass, no tightening loop.
- **Mixed/weaker evidence:** interpersonal coordination, long-running human handoffs, situations where he fully transfers decision authority, and emotional/motivational self-report.
- **Notably absent:** he does not rely on planning rituals for narrow tasks, does not need reassurance or completeness for its own sake, and refuses checks (extra error handling, defensive scaffolding) that duplicate responsibility already living upstream.
- **Counter-pressure exists:** he sometimes requests broad comprehensive exploration — but it's bounded to operationally relevant facts, so it isn't true counter-evidence to the simplification pattern.
- **Confidence collapse zone:** in philosophical/phenomenological exploration lacking concrete anchors (simulation theory, cognitive archetypes), he abandons constraint-seeking and verification loops entirely — the operating system requires physical artifacts or bounded business parameters to engage.

## Counterpart Implications

- **Because he inspects before prescribing, a fitting counterpart leads with a grounded read of the actual object** — surveys the repo, tests the real behavior, surfaces constraints — before offering a recommendation, and presents findings as observation separated from inference.
- **Because he simplifies under pressure, a fitting counterpart proactively questions whether each layer earns its keep** and offers the smaller, more legible version rather than defending elegant structure. Pushback that says "this could just be a config file" feels intelligent, not obstructive.
- **Because he corrects by concretization, a fitting counterpart asks for the missing decision criteria up front** — intended operator, success threshold, what to exclude — so it doesn't have to be told twice. Initiative that bounds the task feels helpful; initiative that expands scope feels intrusive.
- **Because he trusts only fixes coupled to diagnosed causes, a fitting counterpart pairs every change with the cause it addresses and a concrete verification** — never "this should work now."
- **Because he stops once evidence is sufficient, a fitting counterpart matches his pace: fast reconnaissance, early stopping, no broad searching after the answerable core is visible.** Padding the answer after the point is made erodes trust.
- **Because he strips process exhaust, a fitting counterpart keeps output compact and concrete** — no citations, tool chatter, invented frameworks, or references to the interaction itself. The response should be evaluable quickly for substance, scope, and honesty.
- **Because he retains framing authority, a fitting counterpart offers options and tradeoffs but doesn't claim the direction** — it executes bounded operations well and hands back legible work, treating his spec as the boundary.
- **Because his real risk is action-delay through abstraction, a fitting counterpart gently forces the executable next step** — translating insight into structured inputs and concrete commands rather than mirroring the conceptual layer back at him.

## Open Questions

- How does this operating system behave in genuinely interpersonal or political work, where the "real object" is a person, not a system? Evidence is thin.
- Where exactly is his line between "comprehensive enough" and "exhaustive overkill"? The traces show both impulses but not a clean rule.
- Does the inspect-first discipline hold when he's under severe time pressure with a contractual deadline, or does he drop to rough-draft-to-unlock-payment mode? Some evidence suggests the latter.
- How much formal verification does he actually require versus a lighter manual check? The stable signal is "some direct proof," not a specific method.
- In the philosophical/exploratory mode where his constraint-seeking vanishes — is that a deliberate context switch he values, or a blind spot he'd want a counterpart to interrupt?
- How does he handle a collaborator who is *right* but contradicts his framing? Evidence shows retained authority, but not how he metabolizes correct dissent.

## Evidence Fragments

**Inspect-before-prescribe:** "explore this codebase — project type, directory structure, build system, testing setup, linting, code style, existing rules" then "comprehensive summary." / "look at this component and schema, decide and plan whether the pattern is good for a non-technical person."

**Correction by concretization:** "seems overly complex" → "treat this like a hardcoded config file instead of a function store." / "rewrite this to make more sense." / "don't guess," "just answer," "be concise," "grounded in."

**Earn every layer:** "why does the factory need an if-tree if the types already say what should happen," "why keep local error testing if the library already catches it," "are we reinventing the wheel."

**Usability filter:** "is this actually a good pattern for a non technical person?"

**Fix posture:** wants "the actual break point or cause identified," then the repair "checked against the original behavior" — not "it should work now."

**Sequence protection:** "look first," "answer this one first," "outline this first," "decide and plan first."

**Simplification as recovery:** under sprawl, "reduce moving parts, preserve what can be inspected, get to an actionable shape fast."

**Mission:** convert expertise into "usable operating machinery" — agents tied to scripts and task records, leads paired with "the business pain AI could improve," configs collapsed to "one obvious, editable place."

**Action-delay risk:** assistant fails when it provides "conceptual abstraction without implementation scaffolding" — every insight needs "instantaneous translation into structured inputs and specific technical implementation steps."
