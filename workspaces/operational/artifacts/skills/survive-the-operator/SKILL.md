---
name: survive-the-operator
description: Use when the output must be acted on by a specific real operator — a non-technical editor, a coding agent, a reader, or a future handoff — and technical correctness alone won't tell you if it lands. Not needed for throwaway internal scratch work that no one else will run.
compatibility: opencode
---
## When To Use
Load this when work is heading toward handoff or use by someone other than you. The decisive question this user asks is 'is this a good pattern for a non-technical person?' — fit to the real user or maintainer overrides technical cleverness. Mismatch between an artifact and its real operator is high-salience to him.

## Do Not Use
Skip for reversible exploration, rough drafts under time pressure, and personal scratch artifacts where no downstream operator exists yet. Polish for its own sake is overhead; clarity gets enforced only when someone else must act.

## Name The Operator, Then Judge Fit
Before finalizing, name who has to run or maintain this and ask whether they actually can without guesswork.
- For a non-technical user: can they edit the one obvious config place, or does intent hide behind indirection?
- For a coding agent: is the spec complete enough to execute from, with task framing, proof standards, and acceptance criteria explicit? Delegation needs complete specifications, not shared strategy.
- For a reader: does the point and the next step land immediately?

## Decision-Ready Clarity Is The Bar
Good work is comprehensive and simplified at once — it covers the ground without holes and is organized so the operator can act immediately. Detail is not the bar; actionability is. A repository summary must include the concrete build, lint, test, and style rules that make execution possible — not just description.

## Legibility Is Part Of Correctness
Muddy wording is a defect, not a style issue. When meaning is unclear, rewrite it so the meaning and next action surface — treat this as forcing clarity, not cosmetic editing. If the operator would have to interpret or guess, the work is not done.

## The End-Test
Can the intended operator act on this without guesswork or interpretation? If not, the work is operationally unclear regardless of how complete or elegant it is. Reframe the task as evaluating fit against that concrete use case, not against abstract best practice.

## Convert Repeated Judgment Into Machinery
When a task depends on hidden expertise or repeated reconnaissance, encode it once — a config file, a structured record, a guided interface — so it can be rerun and handed off without rediscovering the logic. But only after the need is demonstrated; automation added before proven need reads as premature.

## Failure This Prevents
Operator misfit: producing a pattern that works technically but a real non-technical user or agent couldn't run, and leaving artifacts that force the next person to reconstruct hidden reasoning.
