---
name: bind-to-operator
description: Use when the output must fit the person or role who will run, approve, maintain, or live with it. Owns operator fit only.
category: operator
source_group: hermes-operational
compatibility: opencode
---

## When To Use
Load this when the same artifact, recommendation, workflow, or explanation would need to change depending on who must run it, approve it, maintain it, buy it, or live with its consequences.

The skill owns operator and audience fit. It adapts the work to the person or role that actually has to use it.

## Do Not Use
Do not use this for initial inspection, active-mode routing, tone calibration by itself, structural simplification, or decision packaging. If the operator is already obvious and irrelevant to the output, skip it.

## What To Do
- Identify the operator, audience, maintainer, approver, or buyer with enough specificity to shape the output.
- Ask what they need to do next and what would make the artifact usable for them.
- Adjust detail level, vocabulary, sequence, evidence, and affordances to that operator.
- Do not optimize for the creator's cleverness when the operator needs reliability, speed, or confidence.
- Mark when different operators need different versions.

## Output Shape
Return the operator fit: who it is for, what they need from it, what changes because of that, and the final operator-ready shape.
