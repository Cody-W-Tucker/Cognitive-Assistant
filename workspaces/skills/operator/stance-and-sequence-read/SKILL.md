---
name: stance-and-sequence-read
description: Use when you're unsure whether the user wants orientation, fit judgment, execution, diagnosis, or refinement — and picking wrong would violate sequence integrity. Not needed when the stance is explicit in the prompt.
category: operator
source_group: hermes-operational
compatibility: opencode
---
## When To Use
Load when the request could be answered at the wrong stage — e.g. you might execute when they wanted a plan, or expand scope when they wanted a fix. Useful when the prompt's verbs or framing are mixed or shifting mid-task.

## Do Not Use
Skip for simple factual lookups, one-off how-to questions, and quick troubleshooting, where a direct one-line answer with no scaffolding is correct.

## What This Prevents
Generic agents act before inspecting, expand before framing, or chase the exciting second question before closing the first. Each of these is an order inversion that breaks trust here.

## Reading The Stance
Match verbs and conditions to stance:
- **Orientation/planning** — "look, decide, plan, explore, understand, summarize"; triggered by ambiguity, scope, or misfit risk. Goal: map terrain well enough to judge fit and constraints.
- **Implementation** — an option has cleared three checks: fits real use, matches local conventions, removes avoidable complexity. Now move fast; further analysis is overhead.
- **Direct execution** — prompt already has target + action + output format. Verbs: "rewrite, add, search, note, make." Re-opening scope is the failure.
- **Diagnosis** — behavior diverged from intent. Stop optimizing the old plan; re-baseline into observable conditions, state transitions, and gating rules before continuing.
- **Review/refinement** — standard shifts from "does it work" to "is it legible, usable, minimal." Strip layers, compress, reject minimal compliance.

## The Governing Rule
Earn the right to act by loading the right context first, then refuse to re-open scope once the next move is obvious. Both halves are load-bearing. If confidence drops mid-task, don't patch the old plan — restate the work as observable conditions and gating rules, then proceed.

## Repair Grammar
When something drifts, tighten — never broaden. Recovery means narrower scope, fewer parts, harder proof, not more output. "Do it again, narrower" beats "try again."
