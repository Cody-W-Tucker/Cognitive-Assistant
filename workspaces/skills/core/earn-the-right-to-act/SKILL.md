---
name: earn-the-right-to-act
description: Use when a request is consequential or ambiguous and the temptation is to propose a solution before contacting the real object. Not needed for narrow, fully specified tasks.
category: core
source_group: hermes-operational
compatibility: opencode
---
## When To Use
Load when the task carries architectural, usability, or repository-wide consequences, or when the right move isn't obvious from the prompt. The signal is: ambiguity, scope, or risk that the output won't fit whoever has to use it.

## Do Not Use
Skip entirely when the prompt already contains target + action + output format ("rewrite this," "add these leads," "change this command"). Here an orientation pass is pure overhead and re-opening scope is the failure, not the help.

## What This Prevents
A generic agent jumps to a fluent solution that is technically fine but operationally useless — wrong layer answered, mismatched to the real operator, or unverifiable. This user reads that as false progress and loses trust fast.

## How To Operate
- Open by mapping the terrain, not by prescribing: project type, structure, build/test/lint/style, existing conventions. A missing build/test/lint summary reads as a real gap; decision-irrelevant detail reads as noise.
- Treat action as something the situation must earn through being understood. Present findings as observation separated from inference.
- Stop the survey the moment the answerable core is visible. Front-loaded orientation is justified only because it lets you move fast later — if it keeps expanding past the point where the next move is obvious, that's avoidance, not rigor.
- Before committing to a pattern, run one hard filter: can the actual operator (non-technical editor, coding agent, buyer) use it? A clever pattern they can't operate is a defect, not sophistication.

## Truth-Contact Test
A claim is trustworthy only when tied to the actual file, command, schema, or tested tool behavior. Abstract confidence does not count. If you're reasoning from a remembered template, go read the real thing first.
