## Core Frame

This user’s tacit operating system is built around **securing usable control before committing effort**. In real work, the immediate question is rarely “what is the answer?” It is closer to: *What is the real object here, what constraints govern it, who has to use it, what would count as sufficient proof, and can this be made simpler without losing utility?* The user repeatedly tries to protect against false progress: work that is fluent, elaborate, technically plausible, or conventionally “proper” but not inspectable, usable, grounded, or worth maintaining.

A generic reader may overread the structured prompts as a preference for organization or thoroughness. The deeper pattern is not neatness. The structure is a **control mechanism**. It keeps work in contact with reality, prevents premature abstraction, exposes hidden complexity, and creates a narrow enough surface where judgment can be trusted. The user is not anti-speed, anti-abstraction, or anti-experimentation; they are against committing to any of those before the operating surface is clear enough to inspect.

## High-Leverage Signals

- **Inspection before prescription.**  
  When stakes or ambiguity rise, the user first asks to inspect the existing system: files, schema, component patterns, build setup, tests, linting, style rules, current copy, or actual behavior. This reveals a hidden rule: *recommendations are not valid until they touch the real object.*

- **Complexity must earn its place.**  
  The user repeatedly pushes back on extra layers, function stores, factories, split files, redundant handling, dense copy, or generalized architecture. The standard is not minimalism for its own sake; it is: *every layer must improve legibility, maintainability, usability, or proof.*

- **The intended operator matters early.**  
  A pattern is judged by whether a nontechnical user can actually operate it, whether a maintainer can reason about it, or whether a buyer can recognize the pain point. The user does not treat technical correctness as sufficient if the real operator would struggle.

- **Scope control is a proof strategy.**  
  Lists, checklists, headings, explicit variables, and fixed output shapes are used to prevent drift. They are not merely formatting preferences. They make the work auditable against the requested dimensions.

- **Breakdowns surface as loss of grounding.**  
  The user gets friction when output becomes generic, speculative, too broad, too polished without evidence, or disconnected from the source artifact. Recovery usually means narrowing the task, requiring direct evidence, or restarting from the artifact.

- **Execution is favored once ambiguity is locally bounded.**  
  The user does not want endless planning. Once the object, action, and acceptance criteria are clear, further analysis becomes overhead. Direct commands such as rewrite, add, search, simplify, change, or note usually mean: *do the work, do not reopen the frame.*

- **Durable progress means a smaller, reusable operating surface.**  
  The user is drawn to converting messy judgment into scripts, schemas, configs, task records, lead-enrichment routines, guided interfaces, or repeatable workflows. The goal is often to stop rediscovering the same logic.

- **Correction happens by constraint, not persuasion.**  
  When the assistant misses, the user tends to replace the loose request with stricter boundaries: use this evidence, ignore that, answer in this shape, do not speculate, be concise, ground it in the source.

- **Proof is contextual, not performative.**  
  Citations, tooling chatter, elaborate frameworks, or formal rigor do not automatically increase trust. Trust rises when the answer shows contact with the actual artifact, names the relevant constraints, and makes a bounded claim with visible limits.

## Salience Structure

- **First signal: the real object of work.**  
  The user quickly orients around the concrete thing being acted on: a component, schema, repo, config, command, draft, lead list, page pattern, or observed behavior. Abstract discussion without an object loses force.

- **Second signal: whether the current form is operable.**  
  The user notices whether something can be used, changed, handed off, debugged, or reviewed. A technically correct pattern becomes suspicious if the operator would need too much implicit knowledge.

- **Complexity is salient when it exceeds the task.**  
  The user does not object to complexity categorically. They object when structure becomes more expensive than the job: too many layers, files, abstractions, checks, or words for the current need.

- **Local conventions matter more than generic best practice.**  
  Existing build commands, style patterns, test setup, linting rules, repository structure, and surrounding implementation style become important because they constrain what a good intervention can be.

- **Uncertainty is tolerated when it is bounded.**  
  Rough exploration is acceptable if it is framed as discovery, sampling, or a reversible probe. Unbounded uncertainty triggers inspection, not brainstorming.

- **Generic systems tend to overweight polish and underweight fit.**  
  The user is less impressed by fluent summaries, polished language, or comprehensive frameworks if they do not reduce the next decision. Fit to the user, system, and task carries more weight.

- **Evidence gaps become signal before factual errors do.**  
  The user often reacts not just to wrongness, but to unsupported confidence, scope jumps, and claims that sound plausible without sufficient artifact contact.

## Lived Thresholds

- **Planning is necessary while the object or constraints are unclear.**  
  Verbs like look, inspect, explore, understand, decide, summarize, and plan usually indicate the user has not yet authorized action. The task is still in orientation mode.

- **Planning becomes avoidance once the next move is obvious.**  
  When the prompt already names the object, action, output form, and acceptance criteria, extra analysis is likely friction. At that point, the user expects execution.

- **Roughness is acceptable in reconnaissance.**  
  First-pass summaries, candidate sets, sketches, or probes can be rough if they reduce uncertainty and preserve reversibility. The user does not require polish during early orientation.

- **Roughness stops being acceptable near commitment.**  
  Once a design, fix, message, or architecture is about to be used, the standards tighten: cause must be diagnosed, behavior verified, wording clarified, and unnecessary moving parts removed.

- **Evidence becomes sufficient when it supports the decision, not when the space is exhausted.**  
  The user often wants enough direct context to make a defensible move, not exhaustive research. Stop when the answer is grounded enough and the next action is clear.

- **Uncertainty requires direct inspection when action could create rework.**  
  If a change affects architecture, user experience, codebase conventions, or maintainability, the user tends to pause implementation and require a structured understanding pass.

- **Polish becomes necessary when the artifact faces another human.**  
  Copy, guides, offers, page-building patterns, and nontechnical interfaces need clarity, sequence, and obvious next action. The user tightens wording when interpretation burden would shift to the reader.

- **Confidence drops when the answer outruns its proof base.**  
  Overbroad synthesis, invented frameworks, speculative leaps, or unsupported recommendations trigger narrowing, source checks, or explicit limits.

## Breakdown and Repair

- **Breakdown: the assistant gets ahead of the sequence.**  
  If the user asked to inspect first, answer the first question first, or decide and plan before acting, jumping to implementation creates mistrust.  
  **Repair:** resequence the work: load context, close the first step, then proceed.

- **Breakdown: output is plausible but not grounded.**  
  A fluent answer that does not engage the actual files, text, behavior, or constraints feels weak.  
  **Repair:** return to source material, quote or paraphrase the concrete basis, and narrow claims to what is supported.

- **Breakdown: structure becomes heavier than the job.**  
  Extra abstraction, indirection, configurability, or separation creates drag when it does not visibly buy clarity.  
  **Repair:** collapse the control surface: hardcoded config, fewer files, direct defaults, simpler path, existing hooks.

- **Breakdown: language requires interpretation before action.**  
  Copy or explanation that is technically accurate but awkward, dense, or indirect is treated as unfinished.  
  **Repair:** rewrite for sense, sequence, and obvious next step, not for stylistic flourish.

- **Breakdown: a fix is asserted instead of diagnosed.**  
  Blind patches or “should work now” answers do not satisfy the user.  
  **Repair:** identify the cause, make the smallest relevant change, and verify against the original failure.

- **Breakdown: broad exploration keeps expanding.**  
  When search or analysis becomes too wide, momentum drops.  
  **Repair:** choose a bounded candidate set, inspect targeted windows, stop once the claim is sufficiently supported.

- **Breakdown: inherited best practice becomes unexamined ceremony.**  
  The user resists convention when it survives only because it looks like proper architecture.  
  **Repair:** ask what the layer does, whether the library already handles it, whether types already encode it, or whether one file is easier than several.

## Quality Detection

- **High quality is decision-ready clarity.**  
  The work is good when it exposes the important structure, covers the relevant ground, and makes the next move clear without guesswork.

- **Good work is both simpler and sufficiently complete.**  
  The user does not want shallow minimalism. They want the simplest form that still preserves real utility, including enough concrete detail to act.

- **Proof is contact with the actual environment.**  
  For code, this means files, commands, tests, style, build setup, and current behavior. For business work, it means real buyer pain, actual lead fit, and usable outreach logic. For copy, it means the wording works for the reader’s next action.

- **Weak work is formally acceptable but operationally expensive.**  
  Outputs are rejected or tightened when they sound right but require too much interpretation, maintenance, hidden context, or downstream repair.

- **The user distrusts unearned abstraction.**  
  Frameworks, typologies, generic advice, or elegant architecture are useful only if they clarify the actual task. Otherwise they read as drift.

- **The user also distrusts false completeness.**  
  A long answer that misses build commands, test setup, style rules, real constraints, or user fit is not complete in the way that matters.

- **Quality is detected through usability pressure.**  
  The user often asks: can a nontechnical person use this, can a coding agent act from this, can a maintainer change this, can a buyer recognize this, can I verify this?

## Artifact Relation

- **Artifacts are sources of truth.**  
  Code files, schemas, logs, commands, drafts, lead records, and current UI behavior override abstract guesses. The user wants the assistant to inspect them before concluding.

- **Artifacts are thinking surfaces.**  
  The user uses concrete drafts, configs, summaries, and component patterns to reason. The artifact makes the problem visible enough to judge.

- **Artifacts are debugging surfaces.**  
  Bugs are presented as bounded failure cases: where it happens, what failed, what the visible symptom is, and what context can make diagnosis falsifiable.

- **Artifacts are coordination objects.**  
  A structured summary, executable brief, task record, config file, or repo map allows work to be handed off without relying on hidden conversation context.

- **Artifacts test whether abstraction has drifted too far.**  
  If a proposed system cannot be represented in a small, editable config, clear schema, concrete checklist, or observable behavior, the user tends to distrust it.

- **Direct contact beats reassurance.**  
  The user does not mainly need confidence language. They need the answer to show it touched the thing being discussed.

- **The preferred artifact often centralizes control.**  
  The user repeatedly favors one obvious editable place: explicit defaults, hardcoded config, direct entry points, concise lead fields, or structured task records.

## Mode Shifts

- **Exploration mode begins under ambiguity.**  
  When the system is unfamiliar, the user asks for mapping: project type, directory structure, build, tests, linting, style, rules, candidate files, or current workflow.

- **Planning mode begins when the object is known but the right path is not.**  
  The user asks to decide, compare, judge usability, or plan before implementation. The standard is fit, not possibility.

- **Implementation mode begins when the next action is already constrained.**  
  Direct imperatives indicate that ambiguity has been collapsed: rewrite this, add leads, simplify config, change command, create rule.

- **Diagnosis mode begins when behavior diverges from expectation.**  
  The user shifts to actual versus intended behavior, preconditions, fallback cases, state transitions, and reproduction/verification.

- **Review mode begins when work could pass superficially.**  
  The user then checks whether it is too complex, too vague, missing operational detail, mismatched to the operator, or unsupported by evidence.

- **Refinement mode begins when the artifact is directionally right but still too expensive to use.**  
  The user tightens language, collapses layers, removes redundant checks, or converts vague output into a more obvious handoff.

- **Execution stops and reverts to orientation when assumptions change.**  
  Mid-task changes trigger re-baselining: restate the actual state, intended state, gates, fallbacks, and missing pieces.

## Success Conditions

- **Good execution makes the next step obvious.**  
  It does not leave the user with a broad set of interesting possibilities. It creates a constrained, inspectable path forward.

- **Good execution preserves contact with reality.**  
  It reflects the actual codebase, actual user, actual failure mode, actual buyer pain, or actual wording problem.

- **Good execution reduces unnecessary moving parts.**  
  It removes indirection, duplication, hidden behavior, dense language, and unsupported options unless they clearly earn their cost.

- **Good execution is bounded enough to verify.**  
  The user can tell what changed, why it changed, what evidence supports it, and what remains unresolved.

- **Good execution supports handoff.**  
  A future maintainer, nontechnical user, coding agent, or buyer should not need to reconstruct the hidden logic from scratch.

- **Weak execution creates false momentum.**  
  It sounds productive while increasing ambiguity, maintenance burden, interpretation cost, or risk of rework.

- **Weak execution solves the wrong abstraction level.**  
  It answers the abstract question instead of inspecting the concrete operating environment.

- **Weak execution reopens scope after the user has closed it.**  
  Once the user has specified the action and output, extra strategy or unsolicited frameworks become friction.

## Tensions and Tradeoffs

- **Fast discovery vs high-integrity execution.**  
  The user moves quickly during reconnaissance, sampling, and reversible probes. But once a fix or design is near commitment, correctness, maintainability, and verification outrank speed.

- **Comprehensive orientation vs aggressive simplification.**  
  The user may ask for broad repo understanding, but not for open-ended completeness. The breadth is meant to support later narrowing.

- **Autonomy for helpers vs centralized judgment.**  
  Agents or assistants can scout, retrieve, test, and draft, but the user keeps control of framing, proof threshold, and final judgment.

- **Established paths vs reinvention.**  
  The user is willing to experiment with reversible wrappers, probes, or temporary setups. Structural choices are held to a higher bar and often pulled back toward supported, conventional, or simpler paths.

- **Abstraction as leverage vs abstraction as drag.**  
  The user values schemas, configs, automation, and repeatable systems when they make work easier to run. They reject abstraction when it hides intent or multiplies maintenance surfaces.

- **Roughness as momentum vs roughness as risk.**  
  Rough drafts are fine when they create orientation. They become unacceptable when they face a customer, user, maintainer, or implementation path.

- **Enough evidence vs exhaustive evidence.**  
  The user wants claims grounded enough to act, not research for its own sake. The stopping rule is decision sufficiency.

- **Simplicity vs completeness.**  
  The user does not want stripped-down answers that omit operationally necessary facts. The target is simple enough to use, complete enough to trust.

## Boundary Conditions

- **Strongest in technical, product, architecture, workflow, and implementation-facing work.**  
  The inspect-first and simplify-second pattern is clearest when changes could affect codebases, configurations, interfaces, automations, or maintainability.

- **Strong in revision-heavy communication work.**  
  Copy, sales language, outreach, and guides are judged by whether they make sense, name the pain, reduce density, and make the next action obvious.

- **Strong in ambiguous or unfamiliar systems.**  
  The user prefers a structured discovery pass before acting when the environment is unknown.

- **Relaxed in simple factual lookup.**  
  For narrow questions, the user may ask directly and expect concise answers without decomposition.

- **Relaxed in brainstorming or rough exploratory contexts.**  
  When the user explicitly allows approximation, the strict auditable-scope rule softens.

- **Not a universal preference for minimalism.**  
  The user asks for comprehensive summaries when needed. The real preference is for justified detail, not less detail.

- **Not a blanket rejection of convention.**  
  The user accepts standard engineering loops, MVP framing, tests, small diffs, and repo conventions when they reduce ambiguity and support verification.

- **Evidence is thinner for interpersonal or long-running team dynamics.**  
  The dataset shows structured delegation and assistant coordination more clearly than full human collaboration patterns.

## Open Questions

- How much formal testing does the user require in high-stakes production contexts versus lighter manual verification?

- When does the user choose to preserve a more complex abstraction because future flexibility genuinely outweighs present legibility?

- How does this operating style change in fully collaborative human teams where authority and framing cannot remain centralized?

- What kinds of creative or speculative work does the user consider valuable without immediate operationalization?

- How much of the simplification instinct is driven by time pressure versus a stable architectural philosophy?

- Where does the user’s tolerance for “good enough” end when business, customer, or reliability risk is high?

## Evidence Fragments

### Inspection before action

- “Explore this codebase” by identifying project type, directory structure, build system, testing setup, linting, code style, and existing rules.  
- Look at the specific component and related schema before deciding whether the pattern works.  
- Inspect current implementation before recommending a change.

### Usability and operator fit

- Decide whether a page-building pattern is good for a nontechnical person.  
- Judge the system by whether an actual editor, maintainer, or buyer can use it.  
- Lead research should include each firm’s main pain point and how AI could help.

### Complexity must earn its keep

- A config setup “seems overly complex.”  
- Can this be treated more like a hardcoded config file?  
- Why keep separate files, extra factories, or redundant error handling if they do not improve control?

### Correction by tightening

- “Do not guess.”  
- “Just answer.”  
- Ground the response in the provided material.  
- Rewrite the job with stricter evidence, scope, output shape, and exclusions.

### Quality as operational clarity

- Rewrite this so it “makes more sense.”  
- A summary should include concrete build, test, lint, and style facts, not just a vague overview.  
- Good work is clear enough to act on and complete enough to trust.

### Repair loop

- Identify the actual cause before fixing.  
- Make the smallest relevant change.  
- Verify against the original behavior.  
- If assumptions shift, restate observable conditions, gates, fallbacks, and intended state.

### Automation candidate

- Define objective.  
- Gather operational context.  
- Narrow against user, constraints, and success criteria.  
- Execute against the narrowed frame.  
- Convert repeated judgment into configs, schemas, scripts, task records, or enrichment routines.
