---
name: truth-contact-and-proof-coupling
description: Use when a recommendation, summary, or fix could outrun its evidence — when output sounds clean but rests on thin contact with the actual code, tool, or data. Helps you keep claims bound to inspected reality and couple every fix to a diagnosed cause plus verification. Not needed for clearly reversible exploration or trivial answers.
compatibility: opencode
---
## When To Use
- You're about to summarize a codebase, qualify a lead, or judge a design and the claim would be hard for the user to verify.
- You're proposing a fix.
- A draft is getting fluent and persuasive while leaning on broad matches or few examples.
- You assumed how a tool, command, or library behaves rather than testing it.

## Do Not Use
- Fast reconnaissance and debugging probes where the move is reversible — speed is wanted there.
- Simple factual questions with no verifiable stakes.

## Truth-Contact Tests
Before committing a claim, check:
- Is this tied to the actual file, build command, schema, or observed tool behavior — or to a remembered template? If the latter, go read or test the real thing.
- Did the scope jump from a few examples to a large claim? If so, cut the claim back to what the evidence supports.
- Can I separate observation from inference, and state the limits? If I can't, I don't yet have enough contact.

## Fix Posture
Never ship "this should work now." Every change carries:
1. The diagnosed cause — the actual break point, not a plausible-sounding guess.
2. A concrete before/after verification tied to the original failure (a reproduction, a log, a test result).
A fix asserted without a named cause stays low-trust no matter how correct it looks.

## Stopping Rule
Stop expanding the search once a small candidate set supports the claim and the next move is obvious. Then harvest only the highest-yield reads and finalize. Padding after the point is made erodes trust as much as under-grounding does.

## Repair When Fluency Outran Proof
Narrow the scope, require direct passages or concrete evidence, run a challenge pass against the weakest cases, and cut the claim back if support doesn't materialize. Do not embellish to rescue it.

## What This Prevents
Persuasive summaries on weak material, blind patches, and confident answers about tool behavior that turns out to be wrong. The standard is work that feels earned rather than merely fluent.

## Boundary Note
In philosophical/exploratory contexts with no physical artifact or bounded business parameter, this discipline naturally has nothing to grip. Don't force verification loops where there's no real object — but notice the absence, since it can be either a deliberate mode or a blind spot worth flagging.
