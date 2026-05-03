## Core frame

This user tries to get the real object and the real constraints in view before spending much effort. In practice that means they keep asking some version of the same questions: What are we actually working on? What has to stay true? Who has to use this? What would count as enough proof? Can we make it simpler without making it worse? They are mostly guarding against fake progress: work that sounds competent, looks complete, or follows familiar patterns, but is hard to inspect, awkward to use, or expensive to maintain.

It is easy to misread the structure in their prompts as a love of neatness. That misses the point. The structure is there to keep the work honest. It narrows the surface area, forces contact with the artifact, and makes it easier to tell whether a claim has earned trust. They are fine with speed, abstraction, and experimentation once the object is clear enough to inspect. They push back when those show up too early.

## High-leverage signals

- Inspection comes before recommendation. When the stakes go up or the task gets fuzzy, the user wants to see the files, schema, component, build setup, tests, copy, or actual behavior first. Advice does not count until it touches the thing itself.
- Complexity has to pay rent. Extra layers, split files, factories, generalized architecture, and dense copy all get questioned unless they clearly buy clarity, usability, maintainability, or proof.
- The real operator matters early. The user checks whether a nontechnical person can use it, whether a maintainer can reason about it, or whether a buyer can recognize the pain point. Technical correctness alone does not settle it.
- Scope control is part of verification. Lists, headings, explicit variables, and fixed output shapes are there to stop drift and make the work checkable.
- Breakdowns usually look like loss of grounding. Generic output, speculative claims, broad framing, or polished language without evidence all register as warning signs.
- Once ambiguity is bounded, the user wants execution. If the object, action, and acceptance criteria are already clear, more planning starts to look like stalling.
- Repeated judgment is a candidate for compression. The user often tries to turn messy decisions into scripts, schemas, configs, task records, or other reusable surfaces.
- Corrections usually arrive as tighter constraints. When something misses, the user narrows scope, limits evidence, fixes the output shape, or removes room for guessing.
- Proof is local, not ceremonial. Citations, process chatter, and formal rigor do not help much unless the answer also shows contact with the actual artifact and stays within its evidence.

## Salience structure

- The first thing they look for is the actual object of work: the repo, file, command, schema, draft, UI, lead list, or failure case.
- The next question is whether the current form is usable. Can someone operate it, change it, review it, or hand it off without hidden context?
- Complexity becomes noticeable when it costs more than the job is worth.
- Local conventions matter more than imported best practice. Existing build commands, style rules, tests, structure, and surrounding code shape what a good change looks like.
- Bounded uncertainty is acceptable. Open-ended uncertainty usually triggers inspection, not speculation.
- Polished summaries do not carry much weight if they do not help with the next decision.
- Evidence gaps often matter before outright errors do. Unsupported confidence gets noticed fast.

## Lived thresholds

- Planning is useful while the object or constraints are still unclear.
- Planning becomes drag once the prompt already names the object, action, output, and acceptance criteria.
- Rough work is fine during reconnaissance if it reduces uncertainty and stays reversible.
- Rough work stops being fine near commitment. Before something gets used, the user wants the cause understood, the wording cleaned up, and the moving parts cut back.
- Evidence is sufficient when it supports a defensible next move. The user does not need the whole space exhausted.
- If a change could create rework in architecture, UX, or maintainability, direct inspection becomes mandatory.
- Polish matters more when another human has to read, use, or trust the artifact.
- Confidence drops fast when the answer runs ahead of what the artifact can support.

## Breakdown and repair

- A common failure mode is acting out of order. If inspection or framing was requested first, jumping ahead to implementation damages trust.
- Another failure mode is sounding plausible without showing the basis. The repair is to go back to the file, text, behavior, or trace and narrow the claim.
- The user also reacts when structure gets heavier than the task. The fix is usually to collapse the control surface: fewer files, fewer layers, more direct defaults.
- Dense or indirect language reads as unfinished. The repair is to rewrite for sequence and obvious next action.
- A fix that is asserted instead of diagnosed is not enough. The user wants the cause, the smallest relevant change, and some check against the original failure.
- Wide exploration can become its own problem. When that happens, the user narrows the candidate set and stops once the decision is supported.
- Best practice loses force when it turns into ceremony. The user tends to ask what a layer is actually doing and whether the existing system already covers it.

## Quality detection

- Good work makes the next move clear.
- Good work is simple, but not thin. It keeps the detail needed to act.
- Proof comes from contact with the real environment: files, commands, tests, behavior, buyer pain, user fit, or wording that actually works.
- Weak work sounds acceptable but creates extra interpretation, maintenance, or downstream cleanup.
- The user distrusts abstraction that does not clarify the live task.
- They also distrust long answers that miss the practical facts that matter, like build commands, style rules, current behavior, or operator fit.
- A useful test for quality is whether a nontechnical user, maintainer, coding agent, or buyer could do the next thing without guesswork.

## Artifact relation

- Artifacts are the main source of truth. Code, schemas, logs, commands, drafts, lead records, and current UI behavior beat abstract guesses.
- Artifacts are also thinking surfaces. The user reasons through concrete drafts, configs, summaries, and patterns rather than detached discussion.
- In debugging work, the artifact defines the failure: where it happens, what the symptom is, and what would falsify the diagnosis.
- In coordination work, the artifact carries the handoff. A task record, repo map, config file, or structured summary should reduce dependence on hidden conversation context.
- Artifacts also test whether abstraction has drifted too far. If the idea cannot live in a small editable surface, trust drops.
- Direct contact matters more than reassurance. The user wants to see that the answer touched the thing in question.
- They often prefer one obvious control point: explicit defaults, direct entry points, concise lead fields, or a single structured record.

## Mode shifts

- Exploration starts when the environment is unfamiliar or the task is still blurry. The user asks for mapping: project type, structure, build, tests, lint, style, rules, candidate files, or workflow.
- Planning starts when the object is known but the right path is still open. The standard there is fit, not just possibility.
- Implementation starts when the next action is already constrained. Direct imperatives usually mean the framing work is done.
- Diagnosis starts when behavior and expectation split apart. The focus shifts to state, preconditions, fallbacks, reproduction, and verification.
- Review starts when something could pass on the surface but still be too vague, too complex, or poorly matched to the operator.
- Refinement starts when the artifact is mostly right but still too expensive to use or hand off.
- If assumptions change midstream, execution falls back to orientation. The user re-establishes current state, intended state, gates, and missing pieces.

## Success conditions

- Good execution makes the next step obvious instead of opening new abstract branches.
- Good execution stays tied to the actual codebase, user, failure mode, buyer pain, or wording problem.
- Good execution removes moving parts that are not pulling their weight.
- Good execution is narrow enough to verify. The user can tell what changed, why, and what evidence supports it.
- Good execution supports handoff without requiring someone else to reconstruct the hidden logic.
- Weak execution creates momentum on paper while increasing ambiguity or rework.
- Weak execution answers the wrong level of abstraction.
- Weak execution reopens scope after the user already closed it.

## Tensions and tradeoffs

- The user moves fast during scouting and reversible probes, then slows down near commitment.
- They will ask for broad orientation, but usually to support later narrowing rather than endless coverage.
- Helpers can do real work, but framing, proof threshold, and final judgment stay centralized.
- Experimentation is allowed more often than structural reinvention.
- Abstraction is valuable when it makes operation easier. It is a liability when it hides intent or multiplies maintenance surfaces.
- Roughness is useful during orientation and risky during delivery.
- The user wants enough evidence to act, not exhaustive evidence for its own sake.
- Simplicity matters, but not at the cost of leaving out facts needed for real execution.

## Boundary conditions

- These patterns show up most clearly in technical, product, architecture, workflow, and implementation-facing work.
- They also show up strongly in revision-heavy communication, where density and reader burden matter.
- They get stronger in unfamiliar systems, where the user wants an inspection pass before action.
- They relax for simple factual lookup, where a short direct answer is often enough.
- They also relax in explicit brainstorming or rough exploration, where approximation is allowed.
- This is not blanket minimalism. The user will take detailed output when the detail is justified.
- It is also not blanket anti-convention. Standard loops, tests, small diffs, and repo conventions are welcome when they reduce ambiguity.
- The evidence is thinner for long-running interpersonal dynamics than for direct work execution.

## Open questions

- How much formal testing does the user want in high-risk production work compared with lighter manual verification?
- When does future flexibility justify keeping a more complex abstraction?
- How much does this style change in teams where framing and authority are shared rather than centralized?
- What kinds of creative or speculative work does the user value even when they do not cash out into immediate action?
- How much of the simplification instinct comes from stable philosophy versus time pressure?
- Where does their tolerance for "good enough" end when customer, business, or reliability risk rises?

## Evidence fragments

### Inspection before action

- "Explore this codebase" by checking project type, structure, build, tests, linting, style, and existing rules.
- Look at the actual component and schema before judging the pattern.
- Inspect the current implementation before recommending a change.

### Usability and operator fit

- Decide whether a page-building pattern works for a nontechnical person.
- Judge the system by whether an editor, maintainer, or buyer can actually use it.
- Lead research should include the firm's main pain point and how AI could help.

### Complexity has to pay rent

- A config setup "seems overly complex."
- Could this just be a hardcoded config file?
- Why keep separate files, factories, or redundant error handling if they do not improve control?

### Correction by tightening

- "Do not guess."
- "Just answer."
- Ground the response in the material that was provided.
- Rewrite the job with stricter evidence, scope, output shape, and exclusions.

### Quality as operational clarity

- Rewrite this so it "makes more sense."
- A summary should include build, test, lint, and style facts, not just a vague overview.
- Good work is clear enough to act on and complete enough to trust.

### Repair loop

- Identify the actual cause before fixing.
- Make the smallest relevant change.
- Verify against the original behavior.
- If assumptions change, restate the observable conditions, gates, fallbacks, and intended state.

### Automation candidate

- Define the objective.
- Gather the operating context.
- Narrow against user, constraints, and success criteria.
- Execute inside that narrowed frame.
- Turn repeated judgment into configs, schemas, scripts, task records, or enrichment routines.
