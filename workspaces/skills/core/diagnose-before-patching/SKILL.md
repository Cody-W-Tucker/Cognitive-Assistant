---
name: diagnose-before-patching
description: Use when something is broken, behavior contradicts expectation, or a fix is being proposed. Prevents speculative patches and "should work now" answers by enforcing cause-first, verification-required repair.
category: core
source_group: hermes-operational
compatibility: opencode
---
## When To Use
- A bug, failing test, unexpected output, or behavior mismatch is in scope.
- You are tempted to suggest a change because it "should fix it" or "is probably the issue."
- A previous fix did not stick, or symptoms keep shifting.

## Do Not Use
- Greenfield work where there is no broken behavior to diagnose.
- Style, naming, or refactor requests with no behavioral defect.

## Required Sequence
1. **State current behavior** — what actually happens, observed directly (log, test output, reproduction). Not inferred.
2. **State intended behavior** — what should happen, and under what condition.
3. **Name the cause** — the specific mechanism producing the gap. "Probably related to X" is not a cause; "X is called before Y is initialized, so Z is null at line N" is.
4. **Propose the smallest change addressing that cause.** Not a rewrite, not a refactor bundled in.
5. **Define the verification.** Concrete before/after check: a test that fails before and passes after, a log line, a reproduction that no longer reproduces.

If any step cannot be filled in, stop and surface that gap rather than proposing a patch.

## Failure This Prevents
"Should work now" patches with no diagnosed cause. Fixes that suppress symptoms without addressing mechanism. Plausible changes accepted because they sound reasonable, not because they were verified.

## When Verification Is Hard
If no test, log, or direct check is available, say so explicitly and define the weakest acceptable proxy (e.g., manual reproduction steps, a printed value, a state inspection). Do not let absence of tooling collapse the standard — lower the resolution but keep the verification step.

## Repair Moves
- If a fix has been proposed without a cause, withdraw it. Re-enter at step 3.
- If verification is missing, the repair is not done, regardless of how confident the change feels.
