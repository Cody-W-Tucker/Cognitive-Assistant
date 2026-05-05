# Field Guide: How This User Actually Works

## Core Frame

This user works as an inspector-simplifier. Before doing anything consequential, he forces the work into contact with the actual object — the codebase, the schema, the real operator who will use the thing, the buyer's actual pain — and refuses to act until that contact has occurred. His default move is to convert vague requests into bounded inspection jobs, then collapse the result into the simplest legible structure that still does the job. What he is implicitly protecting against is *false progress*: output that is plausible, elegant, or technically complete but operationally useless, hard to verify, or misaligned with the real user.

A generic reader will likely overweight his "thoroughness" and underweight what that thoroughness is for. He is not careful for its own sake. He front-loads structure so he can move fast later without paying for it in cleanup, drift, or commitments to the wrong abstraction. The simplification habit is not minimalism — it is a control mechanism for keeping work inspectable, reversible, and tied to a real operator.

## High-Leverage Signals

- **Inspection precedes prescription.** Substantive tasks open with "look at this, decide and plan" rather than "do this." He treats the right to act as something earned by first mapping structure, constraints, and intended user.
- **Aggressive consolidation toward config.** When implementations grow factories, branches, and indirection, he reframes them as "treat this like a hardcoded config file." Abstraction has to earn its complexity against a simpler explicit alternative.
- **Audience binding.** He almost never evaluates a pattern in the abstract. He binds it to a specific operator — a non-technical person filling schemas, a coding agent, a buyer who must recognize their own pain — and judges fit there.
- **Correction by concretization, not by complaint.** When work misses, he does not negotiate. He restates the task with tighter constraints, named exclusions, and explicit output shape. "Try again" almost never appears alone.
- **Reversible exploration, irreversible-only-after-proof.** He moves fast in reconnaissance and probes ("for now," "later"), and slows down sharply when a choice would become structural.
- **Sequence protection over speed protection.** He resists the assistant getting ahead of the work — answering question two before question one, coding before inspecting, solving before scoping. The objection is to ungrounded speed, not speed itself.
- **Tightening as recovery.** Under load, drift, or disappointment, he reduces scope and demands concrete evidence rather than expanding effort.
- **Standards he will not relax under pressure:** usefulness, verifiability, fit to operator. Standards he relaxes early: completeness, generality, architectural elegance.

## Salience Structure

- **First salient: the operator.** Who has to use, maintain, or run this? Pattern goodness collapses to fit-for-this-person.
- **Second salient: complexity that has not earned its keep.** Indirection, factories, configurable layers, defensive scaffolding, and dense wording register quickly as drag.
- **Third salient: gap between described behavior and actual behavior.** A fix that "should work" is not signal. A fix tied to a diagnosed cause and a verification step is signal.
- **Background until it breaks: existing project conventions.** He does not impose taste on unfamiliar codebases; he asks for build, test, lint, and style first, then matches.
- **Underweighted by generic readers:** how much of his "thoroughness" is actually scope-narrowing in disguise. The checklists are reductive, not exhaustive.
- **Overweighted by generic readers:** the appearance of process-heaviness. He uses lightweight scaffolding, not ritual; he drops it instantly for narrow factual queries.

## Lived Thresholds

- **Planning becomes avoidance** when the next move is already obvious — a named target, a concrete object, a clear deliverable. At that point further analysis reads as overhead and he switches to imperative phrasing.
- **Roughness is acceptable** during reconnaissance, probes, scouting passes, and "for now" wrappers — anything reversible.
- **Roughness stops being acceptable** once the work would lock in structure, ship to a non-technical user, or compound across future tasks.
- **Evidence is sufficient** when a small candidate set is targeted, the strongest passages have been read directly, and a challenge pass has not weakened the claim. He stops there rather than expanding the search.
- **Polish matters** when an artifact must survive contact with a specific operator: copy a buyer must immediately understand, code an agent must execute, a summary that must drive a next action.
- **Uncertainty forces inspection** when the task has architectural, usability, or repository-wide implications, or when the abstraction level of the request feels off.
- **Confidence drops** when output is fluent but the proof base is thin — broad pattern claims from few examples, generalization that outruns the inspected material.

## Breakdown and Repair

- **Breakdown signal: ungrounded fluency.** Output sounds clean while leaning on broad matches or speculative inference. Repair: narrow scope, demand directly supported passages, cut the answer back rather than embellishing.
- **Breakdown signal: complexity exceeding need.** Setup "seems overly complex." Repair: collapse toward config, remove a file boundary, delete redundant defensive code, name a simpler model ("treat this like X, not Y").
- **Breakdown signal: inverted sequence.** Assistant produces output before inspecting, or answers part two before part one. Repair: re-issue the prompt with explicit ordering and "first / then" structure.
- **Breakdown signal: misfit to operator.** A pattern that works for the engineer but not for the schema-editor. Repair: reframe judgment criterion as the specific user's experience, not the code's elegance.
- **Breakdown signal: scope creep on synthesis.** Conclusions extend beyond the evidence. Repair: remove interpretive slack — "do not guess," "read that," "grounded in," "just answer."
- **Breakdown signal: fix without diagnosis.** A patch that might work. Repair: require the cause, the smallest change addressing that cause, and a concrete before/after check.
- **Recovery is constraint-based, not encouragement-based.** He restores momentum by reducing surface area, not by adding effort.

## Quality Detection

- **Strong:** decision-ready clarity. The artifact can be acted on by the named operator without further interpretation.
- **Strong:** the result names what was inspected, what the rule is, what it does operationally, and where it doesn't apply. Observation and inference are separated.
- **Weak:** technically correct but operationally heavy — extra abstraction, hidden behavior, dense wording, unnecessary files.
- **Weak:** comprehensive in form but disconnected from the real use case or the actual repository conventions.
- **Distrusts:** plausibility, elegance, polish, "best practice by convention," and any output containing performative scaffolding (citations, tooling chatter, invented frameworks, meta-commentary).
- **Trusts:** concrete artifact + plain interpretation + explicit limits. Bounded coverage organized by decision use, not by topic.
- **A repository summary is not done** until it lists build, test, lint, style, and existing rules — the things needed to actually work in the codebase.
- **Copy is not done** when it is correct; it is done when the next action is obvious.

## Artifact Relation

- **Artifact as source of truth.** Before judging a pattern, he wants to look at the actual component and schema together. Abstraction without artifact contact is treated as guessing.
- **Artifact as thinking surface.** He uses checklists (project type, structure, build, tests, lint, style, rules) as structured probes that force coverage and prevent omission, not as documentation.
- **Artifact as drift detector.** When an explanation feels too clean, he goes back to the file, the failing command, the actual log output. If the artifact does not support the claim, the claim is wrong.
- **Artifact as operator stand-in.** He simulates the non-technical user moving through the schema, or the coding agent reading the spec, and judges the work by what they encounter.
- **Artifact preferred over rationale.** A working config someone can edit beats a flexible system that requires explanation. The thing-in-hand is the standard.
- **Code, schema, and config sit higher than commentary.** Process talk, citations, and tool references are stripped from outputs because they crowd out the artifact.
- **Crisp intermediate artifacts restore traction** when energy drops — a smaller summary, a scoped plan, a config sketch — because they make progress visibly inspectable.

## Mode Shifts

- **Exploration → planning** triggers on "decide and plan," "is this a good pattern," "summarize." Verbs change from imperatives to inspection verbs.
- **Planning → implementation** triggers when the object, the action, and the deliverable are all named in the prompt. Imperative verbs return; explanation requests disappear.
- **Implementation → diagnosis** triggers when behavior contradicts expectation. He stops optimizing the old plan and rewrites the task as observable conditions: what should happen first, what only after a status exists, what the fallback is.
- **Diagnosis → repair** requires a named cause before a change is allowed. Speculative patches are rejected.
- **Repair → verification** is non-optional in technical work. Some direct proof is required — a test, a reproduction, a log, a behavior check.
- **Any mode → re-baselining** triggers when assumptions shift mid-task. Momentum stops; current behavior, intended behavior, and gating rules are restated before continuing.
- **Across all modes:** standards of usefulness and verifiability are constant. Standards of breadth, completeness, and elegance vary by mode.

## Success Conditions

- **Good execution:** produces a small, inspectable artifact that survives contact with the named operator and removes ambiguity for the next move.
- **Good execution:** stays inside the constraint surface he set; does not import unrequested frameworks, polish, or scope.
- **Good execution:** when uncertain, narrows and stops. When confident, names limits explicitly.
- **Good execution:** matches existing project conventions before introducing new ones.
- **Weak execution:** elaborates, generalizes, or polishes when narrowing was needed.
- **Weak execution:** answers from probability rather than from the artifact.
- **Weak execution:** completes the form of the task (sounds like a summary, looks like a fix) without doing the operational work (driving the next action, addressing the diagnosed cause).
- **Weak execution:** treats viability as sufficient. He picks among viable paths by simplicity, fit, and convention — not by what is buildable.

## Tensions and Tradeoffs

- **Speed vs rigor:** he wants both, and resolves the tension by allocating speed to reconnaissance and rigor to commitment. Speed in the wrong phase reads as carelessness; rigor in the wrong phase reads as overhead.
- **Comprehensive vs minimal:** he asks for "comprehensive summaries" and also strips complexity aggressively. The reconciliation is that comprehensiveness applies to *operationally relevant facts*, not to general coverage.
- **Delegation vs control:** he delegates execution freely (scout, retrieve, draft) but never delegates the standard of proof, the framing, or the final synthesis.
- **Abstraction vs reality-contact:** he uses structure as a control tool but distrusts abstraction that has drifted from the artifact. Structure is allowed; floating abstraction is not.
- **Inherited vs self-authored convention:** he adopts standard engineering process easily (small diffs, MVP, verify-after) but rejects inherited architectural defaults (factories, configurability, defensive scaffolding) that have not earned their cost.
- **Stated ideal vs real behavior:** he frames work as "decide and plan," but once a task is concrete he wants imperative execution and treats further planning as drag. The ideal is conditional, not universal.
- **Vision authority vs collaborative shaping:** he retains directional authority and uses collaborators to clarify, not to co-author paradigm choices.

## Boundary Conditions

- **Strongest patterns:** codebase exploration, architecture/config simplification, prompt and system-message design, non-technical UX evaluation, debugging with verification, lead qualification with explicit pain-point binding.
- **Relaxes for:** simple factual questions, lookups, quick how-to queries. Short prompts, no scaffolding, no tightening loop.
- **Mixed evidence:** how this logic transfers to purely interpersonal work, time-management overload, or long-running human handoffs. The dataset shows task-shaping more than emotional load management.
- **Specific exception:** in philosophical, phenomenological, or speculative discussion, the artifact-anchoring and verification loops drop entirely. He tolerates ungrounded narrative there in a way he never tolerates in technical work.
- **Strain mode:** under pressure he does not relax usefulness or verifiability — he relaxes generality, polish, and architectural ambition.
- **Energy peak:** when a vague human problem becomes a working system. Lowest tolerance for friction: complexity that does not yet earn its cost.

## Open Questions

- How far this inspection-first logic extends into work without a clean artifact (organizational decisions, hiring, partnership choices).
- Whether his rejection of "best practice by convention" survives in domains where conventions have safety or compliance weight he hasn't encountered yet.
- Where his tolerance for ungrounded speculation in non-technical reflection actually ends, and whether that tolerance has cost.
- How he handles genuine collaborative authorship — the dataset shows constrained delegation, not shared paradigm shaping, and it is unclear how he behaves when an equal partner pushes back on framing.
- Whether the "treat it like a config" instinct has a failure mode at scale he has not yet hit.
- How the verification standard adjusts when no test, log, or direct check is available.
- Whether the mission-level interest in operationalizing knowledge will eventually conflict with the simplification instinct, since real operationalization tends to grow structure.

## Evidence Fragments

**Inspection precedes prescription**
- "look at the existing component and schema, decide and plan whether the pattern is good for a non-technical user"
- "explore the codebase: project type, structure, build system, testing setup, linting, style, existing rules"

**Consolidation toward config**
- "seems overly complex — can it just be a hardcoded config file instead of a function store?"
- "why does the factory need an if-tree if the types already say what should happen?"

**Audience binding**
- "is this actually a good pattern for a nontechnical person to use?"
- lead notes paired with "biggest pain point and how AI would help"

**Correction by concretization**
- "don't guess," "do not guess," "read that," "just answer," "grounded in"
- rewrites with named exclusions and explicit output shape rather than "try again"

**Sequence protection**
- "first answer the first question, then move to the second"
- "first outline the customer types, then go deeper"

**Tightening as recovery**
- "rewrite this so it makes more sense"
- requests narrowed from "how do I use this tool?" to "what does this actually do, and what would I need instead?"

**Verification non-optional**
- repair loops requiring cause + smallest change + before/after check
- rejection of fixes presented as "should work now" without diagnosis

**Reversible exploration markers**
- "for now," "later," wrapper-around-existing-tool patterns used as probes rather than commitments
