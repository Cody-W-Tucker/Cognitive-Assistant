---
name: verify-before-trust
description: Use when a fix, summary, or design judgment could be asserted without being coupled to a diagnosed cause and a concrete verification. Not needed when the claim is already tied to inspected evidence.
source_group: group-3
compatibility: opencode
---
## When To Use
Load when you're about to claim something works, summarize a system, or trust a fix. Especially relevant for bug fixes, tool behavior assumptions, and any summary that drives a downstream decision.

## Do Not Use
Skip when the answer is a direct factual lookup with no action riding on it, or when contact with the real object has already been made and bounded.

## What This Prevents
The blind patch — a fix asserted without a diagnosed cause ("this should work now") — stays low-trust here regardless of how clean it looks. Same for persuasive summaries built on thin contact with the material.

## Verification Defaults
- Pair every change with the cause it addresses plus a concrete before/after tied to the original failure. No cause, no trust.
- Prefer observable evidence over reasoning: ask a broken command to emit a usable log rather than debugging abstractly; test tool behavior manually instead of assuming it.
- When a tool surprises you, narrow the question from "how do I use this?" to "what does this actually do, and what would I need instead?"
- For drafts leaning on weak signals: require direct passages, run a challenge pass against the weakest cases, and cut the claim back if support doesn't materialize — don't embellish to cover the gap.

## Quality Tells
- **Shallow:** plausible-but-unverifiable, can't drive the next action, needs interpretation before it communicates.
- **Earned:** separates observation from inference, states its own limits, anchored to the real use case.
- Detail alone is not quality. Decision-ready clarity that covers the relevant ground and stays anchored to the real operator — all three at once — is.

## Boundary
When the domain has no physical artifact or bounded parameter to test against (open-ended conceptual or phenomenological work), this verification instinct has nothing to grip. Don't fake rigor by inventing anchors; name the absence instead.
