---
name: verify-before-trust
description: Use after a claim or change needs proof before it is trusted. Owns post-claim and post-change verification only.
category: core
source_group: hermes-operational
compatibility: opencode
---

## When To Use
Load this after a claim, fix, rewrite, migration, generated artifact, or handoff needs proof before it is trusted. The skill owns post-claim and post-change verification.

Use it when the work is already asserted as done, correct, aligned, or improved, and the next responsible move is to test that assertion against evidence.

## Do Not Use
Do not use this for initial inspection, root-cause diagnosis, mode selection, decision packaging, or action-forcing. It starts after there is something specific to verify.

## What To Do
- Identify the claim being tested in one sentence.
- Choose the smallest verification that actually bears on that claim: test, lint, diff, rendered output, replayed workflow, checksum, manual check, or acceptance command.
- Report the result without laundering uncertainty. Passing a narrow check proves only the narrow claim.
- If verification is blocked, state the blocker and the next evidence needed.
- Do not substitute confidence, consistency, or intention for proof.

## Output Shape
Return the claim, verification performed, result, and any remaining unverified surface.
