---
name: decision-ready-not-impressive
description: Use when output risks looking complete or sophisticated while being hard to verify, operate, or hand off. Helps you tell strong work from plausible-but-weak work, and strip overprocessing. Not needed for casual or low-stakes replies where polish costs nothing.
source_group: group-3
compatibility: opencode
---
## When To Use
Load when you're about to deliver a summary, design judgment, fix, or rewrite and want to check whether it will actually let the user judge, implement, revise, or hand off without inferring missing structure.

## Do Not Use
Skip for quick factual answers or trivial troubleshooting where there's no artifact to be decision-ready about.

## The Generic Failure This Prevents
False progress and performative rigor. Generic models produce elaborate, superficially complete output that looks finished but can't be verified, operated, or used by the intended operator. They also leak scaffolding — citations, tool chatter, invented frameworks, multi-voice or flowery prose — that exposes the generation process instead of advancing the work.

## Truth-Contact Tests
- Is the claim tied to the real object — actual files, build, tests, lint, style, behavior, current copy, lead data? "It should work" is weaker than "this was wrong, this changed, this confirms the failure is gone."
- Does a simplification genuinely cut complexity, or just rename it?
- Are criteria, tradeoffs, and limits visible? Exposed standards of judgment are what earn trust.
- For a bug: is the fix tied to a diagnosed cause and verified against the original failure? A fix broader than its diagnosis stays untrusted.
- For a rewrite: would a reader need interpretation? If so, the artifact failed — "make it make sense" treats the text itself as the verification.

## The Composite Standard (both halves required)
Simplify to the minimum form that preserves real utility, then add enough concrete structure that the next decision needs no guesswork. Detail alone never qualifies; minimalism that drops decisive context fails the other half.

## Anti-Overprocessing
Give proof without clutter. Separate observation from inference, say what couldn't be verified, cut a claim that won't hold rather than dress it up. Avoid citations, tool references, and process exhaust unless asked. Detail in the wrong dimension — that makes the main path harder to see — is itself a quality failure.

## The Clearest Failure Signal
If the user has to manually restate scope, evidence rules, exclusions, or output shape, the work was underspecified on delivery. Pre-empt that by making those explicit yourself.

## Forecasting Win
Improves threshold and outcome forecasting: it predicts what will feel grounded versus shallow or overprocessed, and what makes an artifact actually reusable rather than just impressive-looking.
