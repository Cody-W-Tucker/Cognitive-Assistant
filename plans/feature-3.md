# Feature 3: make proposals reward-weighted

Goal reference: `IDEA.md`. After feature 2, what survives is chosen by the
reward, but what gets tried is still drawn from conformity gaps. This feature
makes the proposal step prefer gaps from sessions where the person did not
move. Start only after feature 2 has produced at least two real verdicts, so
the outcome labels have been checked in use.

## Scope

1. **Carry the outcome into fold** (`improve/src/fold.js`).
   Each cluster records, over its supporting sessions: counts of `advanced`,
   `stalled`, `regressed`, `unclear` and unscored. No model call.

2. **Rank eligible clusters.**
   - Weight = stalled + regressed sessions, then total sessions, then recency.
   - A cluster supported only by `advanced` sessions stays eligible but ranks
     last: the mistake did not stop the person.
   - `--min-gap-evidence` is unchanged.

3. **Show the weight to synthesis and annotate.**
   - `improve/prompts/synthesis.md`: each cluster line carries its outcome
     counts; instruct the model to plan the highest-weight clusters first.
   - `improve/prompts/annotate.md`: a kept record's evidence must include at
     least one session labelled `stalled` or `regressed`, when the cluster
     has one.
   - Give both stages the active records, capped by section rather than by a
     single cut from the start, so they stop re-planning adopted gaps
     (`improve/src/soul.js`, around line 8).

4. **Retire fixed gaps** (`improve/src/propose.js`, around 14-24).
   Add accepted records' `clusterId`s to the suppression set, with the same
   exception as rejections: new sessions dated after the adopting generation
   re-open the cluster.

5. **Auto adoption order** (`core/improve.py` `_auto_candidate`).
   Adopt the highest-weight kept record, not the first. Exclude ids that are
   already active as well as reverted.

6. **Decide the improvement rule.** With real verdicts in hand, decide
   whether `keep` should require the miss rate not to rise (today) or to fall.
   This is the person's decision; the plan only records the outcome in
   `docs/Living-SOUL.md` and implements the chosen rule in
   `core/outcome.py`.

## Out of scope

- More than one change under test at a time.
- Proposal kinds other than `add`.
- Outcome evidence from new sources (for example the Langfuse route labels).
  Note it as a candidate if the `unclear` share is high.

## Tests

- Node: cluster outcome counts; ranking order; accepted clusters suppressed
  and re-opened by later sessions; annotate validation of the
  stalled/regressed evidence rule.
- Python: `_auto_candidate` picks by weight and skips active ids.

## Docs

`docs/Improvement-Loop.md` (fold, synthesize, annotate, propose) and
`docs/Living-SOUL.md` (adoption order, the improvement rule).

## Done when

- A proposal lists its edits in weight order with outcome counts visible.
- No adopted cluster is re-proposed on the sessions that produced it.
- Both test suites pass.
