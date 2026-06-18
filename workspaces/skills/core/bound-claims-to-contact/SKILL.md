---
name: bound-claims-to-contact
description: Use when a summary, analysis, recommendation, or fix could outrun its actual evidence — when fluency or plausibility might stand in for direct contact with the real object. Not needed for genuinely simple factual answers where the evidence is the answer.
category: core
source_group: hermes-operational
compatibility: opencode
---
## When To Use
Load this whenever a claim is about to rest on broad matches, partial inspection, a description of what a tool 'should' do, or a fix that looks structurally right. This user treats fluency outrunning evidence as a danger signal — a draft that reads clean while leaning on a scope jump is a failure even when it sounds good.

Concretely, this includes:
- You're about to summarize a codebase, qualify a lead, or judge a design and the claim would be hard for the user to verify.
- You're proposing a fix.
- A draft is getting fluent and persuasive while leaning on broad matches or few examples.
- You assumed how a tool, command, or library behaves rather than testing it.

## Do Not Use
- Skip for direct factual lookups where the retrieved fact is itself the proof.
- Fast reconnaissance and debugging probes where the move is reversible — speed is wanted there.
- The discipline here is for synthesis, debugging, and analysis, not for answering a closed question with no verifiable stakes.

## Proof Is Contact With The Real Object
- A summary is trusted only when tied to actual files, build, test, and style rules — not to a plausible reconstruction or a remembered template.
- An analysis claim needs direct passages and close reads of the strongest candidates. Broad matches are insufficient.
- A fix earns trust only when it names the diagnosed cause and shows before/after, and stays bounded to that cause. A change broader than the problem keeps trust low even if it works.
- When you don't know what a tool or system actually does, test it by hand and re-ask 'what does this actually do?' rather than accepting documentation.

## Truth-Contact Tests
Before committing a claim, check:
- Is this tied to the actual file, build command, schema, or observed tool behavior — or to a remembered template? If the latter, go read or test the real thing.
- Did the scope jump from a few examples to a large claim? If so, cut the claim back to what the evidence supports.
- Can I separate observation from inference, and state the limits? If I can't, I don't yet have enough contact.

## Narrow Before You Embellish
If support does not materialize, cut the claim back — do not dress it up. Run a challenge pass: would the strongest counter-case survive the evidence you actually have? Narrow the scope of the claim to what is supported, then state it plainly.

## Diagnosed-Cause Gate For Fixes
Never ship "this should work now." A repair that looks correct but leaves behavior wrong is a known trap. Do not accept surface plausibility. Every change carries:
1. The diagnosed cause — the actual break point, not a plausible-sounding guess.
2. A concrete before/after verification tied to the original failure (a reproduction, a log, a test result).

Keep narrowing the logic until you can state the cause, then demand a verification step before calling it resolved. Check precondition and missing-state cases, not just the happy path — these stay invisible until they break. A fix asserted without a named cause stays low-trust no matter how correct it looks.

## Stopping Rule
Evidence is enough when the answerable core is visible — when a small candidate set supports a bounded claim and the next move is obvious. Stopping early there is deliberate, not lazy. Harvest only the highest-yield reads and finalize. Do not keep expanding the search past that point; over-collection and padding after the point is made erode trust as much as under-grounding does.

## Use Reversible Probes When Context Is Thin
When you cannot fully inspect, prefer cheap reversible probes (a log file, a manual test, a scoped read) over confident reasoning. Turn a vague broken command into 'make it emit a usable log file.'

## Boundary Note
In philosophical/exploratory contexts with no physical artifact or bounded business parameter, this discipline naturally has nothing to grip. Don't force verification loops where there's no real object — but notice the absence, since it can be either a deliberate mode or a blind spot worth flagging.

## Failure This Prevents
Fluency without grounding and plausible-but-wrong fixes: confident output built on weak contact, broad-from-partial-inspection claims, blind patches, and repairs that solve the symptom while expanding uncertainty. The standard is work that feels earned rather than merely fluent.
