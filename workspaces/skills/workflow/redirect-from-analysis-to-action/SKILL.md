---
name: redirect-from-analysis-to-action
description: Use when enough analysis exists and the next move must become concrete. Owns action handoff only, not mode detection.
category: workflow
source_group: hermes-existential
compatibility: opencode
---

## When To Use
Load this when the user already has enough understanding and the conversation is continuing as analysis, framing, or synthesis instead of producing the concrete move. The skill owns the handoff from thinking to action.

Use it when the next useful artifact is a message, decision, experiment, boundary, request, implementation step, or proof threshold.

## Do Not Use
Do not use this to decide whether the user is avoiding, misaligned, in discovery, or in repair. Do not use it for tone calibration, audience fit, structural simplification, or relational ownership sorting. It starts after action is the correct next mode.

## What To Do
- Compress the existing analysis to the one conclusion that matters.
- Name the concrete move being avoided or delayed.
- Convert the discussion into a small action with an owner, recipient, time box, or proof threshold.
- Preserve only the context needed to make the action clean.
- If action is not yet justified, stop and route to inspection, diagnosis, or motive discrimination instead.

## Output Shape
Return the commitment shape: the conclusion, the move, the smallest executable version, and the evidence that it happened.
