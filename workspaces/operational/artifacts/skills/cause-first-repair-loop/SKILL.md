---
name: cause-first-repair-loop
description: Use when behavior diverges from expectation and a fix would be risky without identifying the actual cause first.
compatibility: opencode
---
## When To Use
Use this for bugs, regressions, broken commands, failing tests, UI mismatches, data issues, automation failures, or any request where the visible symptom might invite a blind patch.

This helps when the task requires diagnosis, a small relevant change, and verification against the original failure.

## Do Not Use
Do not use for simple requested edits, cosmetic changes, or cases where the user has already identified the exact cause and only wants the patch applied.

## Failure This Prevents
Prevents asserted fixes: changes that may look plausible but do not explain the failure, may patch the wrong layer, and are not verified against the behavior that originally broke.

## Repair Sequence
Follow this order:

1. **Restate the failure boundary**
   - What is happening?
   - What should happen?
   - Where does it happen?
   - What input, state, or command triggers it?

2. **Inspect the relevant path**
   - Start at the symptom.
   - Trace to the nearest responsible code, config, data, or state transition.
   - Prefer targeted inspection over broad exploration.

3. **Name the cause**
   - Identify the mechanism, not just the symptom.
   - If there are multiple candidates, rank them by evidence.
   - Label uncertainty instead of pretending certainty.

4. **Make the smallest relevant change**
   - Patch the cause, not the surface symptom.
   - Avoid opportunistic refactors.
   - Preserve local conventions.

5. **Verify against the original failure**
   - Run the narrowest available test, command, reproduction, or manual check.
   - If verification is not possible, state exactly what remains unverified.

## Diagnostic Questions
Use only the questions needed to close the failure boundary:

- What changed recently?
- Is the failure reproducible?
- Is it data-specific, environment-specific, or path-specific?
- Does the existing code already have a fallback or convention for this?
- Is the visible error upstream or downstream from the real cause?

Avoid turning diagnosis into open-ended investigation once the cause is sufficiently supported.

## Patch Discipline
During the fix:

- keep the diff small
- do not introduce extra abstraction unless the cause requires it
- do not add redundant error handling if the platform or library already handles the case
- do not silently change behavior outside the failure boundary
- do not claim success without verification

## Report Shape
When finished, use a compact report:

- **Cause**: the concrete mechanism that produced the failure
- **Change**: the smallest relevant fix made
- **Verification**: command, test, or check run
- **Remaining risk**: only if something could not be verified

## If Assumptions Shift
If inspection shows the original framing was wrong:

1. Stop patching.
2. Restate the new observable facts.
3. Re-identify expected versus actual behavior.
4. Continue from the updated failure boundary.
