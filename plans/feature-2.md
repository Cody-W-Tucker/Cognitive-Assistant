# Feature 2: replace the reward

Goal reference: `IDEA.md`. This replaces the conformity-based miss with a
delayed, blind outcome signal: did the session move the person, judged from
evidence outside the transcript. Requires feature 1 items 1-7.

Status (2026-11-14): implemented, backtest not yet run. Differences from the
text below, decided while building:

- **Later sessions do not need a directory.** Most Hermes sessions have no
  `cwd` by design. Every later Hermes session in the window is a candidate
  (earliest eight); the judge decides which continue the same aim.
- **The end of a session is its last activity**, not Hermes's `ended_at`,
  which is stamped when an idle session is reaped.
- **No failure states.** A session that cannot be scored is left without an
  outcome and tried again later. There are no reason codes and no failure log.
- **The trace is a snapshot from analysis time**, valid while the session's
  messages are unchanged. A dry run reads unanalyzed sessions directly, which
  is what makes the backtest possible on a fresh CA home.
- **A fifth label, `answered`.** The first backtest rows scored quick
  questions as `advanced` because nothing contradicted them. A question the
  reply settled now gets its own label and stays out of verdicts.
- **Commits come from the repositories a session's tool calls touched**, not
  only from a recorded repository, which most Hermes sessions lack.
- **Journal evidence is keyword search and will rarely match.** Linking
  sessions and notes by topic similarity is a later plan addition.

## Design

A new `outcome` stage, separate from `analyze`.

- **Blind.** The prompt contains no SOUL, posture or records. Both sides of a
  verdict are judged by identical text.
- **Delayed.** A session is scored once it has matured: `--mature-days` after
  it ended (default 3), so follow-up evidence exists.
- **Once.** A session gets one outcome, stamped with its rubric. It is
  re-scored only by an explicit backfill after a rubric change.
- `analyze` is unchanged and remains the source of gaps and records only.

## Scope

1. **Follow-up collector** (`improve/src/followup.js`, no model call).
   For one session, gather evidence dated inside
   `[endedAt, endedAt + mature-days]`:
   - **Later sessions:** sessions from any readable harness with the same
     `gitRepoRoot`, else the same `cwd`, else none. Keep the first user
     message and the last assistant message of each, clamped.
   - **Commits:** `git log` in `gitRepoRoot` for the window (hash, date,
     subject). Skip silently when there is no repo.
   - **Journal:** `qmd` query built from the session's first user message,
     limited to notes dated inside the window. Optional; a missing `qmd` or
     an empty result is recorded as `none`, never an error.
   Each item carries a short source ref (`session:<id>`, `commit:<hash>`,
   `note:<docid>`), which the judge must cite.

2. **Outcome prompt** (`improve/prompts/outcome.md`).
   Inputs: the distilled session (head and tail) and the follow-up evidence.
   Output, one JSON object:
   ```
   {
     "aim": "what the person was trying to reach, one sentence",
     "label": "advanced | stalled | regressed | unclear",
     "reason": "one sentence",
     "evidence": [{"ref": "session:<id> | commit:<hash> | note:<docid> | trace", "quote": "verbatim"}]
   }
   ```
   Rules in the prompt: name the aim before judging; a count of commits or
   messages is never sufficient; `advanced` needs evidence the aim was reached
   or materially closer; `stalled` when the same aim recurs without progress
   or the session ends without the thing asked for; `regressed` when later
   evidence shows the work was undone or redone; `unclear` when the evidence
   does not decide. Prefer `unclear` over a guess.

3. **Outcome stage** (`improve/src/outcome.js`).
   - Validates the reply: label in the set, at least one evidence item for any
     label other than `unclear`, every `ref` present in the supplied
     follow-up or equal to `trace`, every `trace` quote found in the distilled
     trace. An invalid reply is recorded as failed and retried next run.
   - Writes `outcome: {aim, label, reason, evidence, rubric: {promptSha,
     model}, scoredAt}` into the session's evidence file. Never touches the
     `positive` / `negative` / `gaps` arrays.
   - Model role `OUTCOME` (`CA_LLM_MODEL_OUTCOME`), same tool-free call path
     and cache as the other roles. Mock analyzer support for tests.

4. **Wire into the runtime.**
   - `improve/src/pipeline.js`: after analyze, run the outcome stage over
     evidence that is `status: ok`, matured and has no outcome.
   - `improve/bin/ca-improve.js`: new command `outcome` with
     `--since`, `--limit`, `--dry-run`, `--rescore`. `--dry-run` writes
     results to `<state>/outcome-preview/<runId>.jsonl` and leaves evidence
     untouched.
   - `core/cli.py`: `python -m core improve-outcome` passing those flags.

5. **Verdicts read the outcome** (`core/outcome.py`).
   - `is_miss`: `stalled` or `regressed` is a miss, `advanced` is not,
     `unclear` is excluded from both the miss count and the session count.
   - A session with no outcome yet is excluded (it has not matured).
   - Rubric check from feature 1 now applies to `outcome.rubric`.
   - No fallback to the conformity rule. A generation whose sessions lack
     outcomes is `pending`.
   - Verdict rows record `improved: true` when the miss rate fell with the
     same z magnitude. This is reporting only; the keep/revert rule does not
     change in this feature.

6. **Docs.** `docs/Improvement-Loop.md` (new stage, command, role variable),
   `docs/Living-SOUL.md` (what a miss is, maturation, `unclear`),
   `docs/CLI-and-Command-Reference.md`.

## Out of scope

- Using outcomes to rank proposals (feature 3).
- Changing the decision rule to require improvement.
- Sources outside the feature 1 allowlist.

## Tests

- Node: collector window boundaries and each source absent; validation
  rejects an uncited ref and a quote not in the trace; dry run leaves
  evidence unchanged; an immature session is skipped.
- Python: `is_miss` per label; `unclear` and unscored sessions excluded;
  rubric mismatch gives `pending`; `improved` flag.

## The backtest (run once, by the person)

After merge, on the machine holding the Hermes store:

```bash
python -m core improve-outcome --since 70d --dry-run
```

About 200 sessions, one model call each. Then:

1. Read 20 preview rows together and compare the labels with the person's own
   read. Adjust the prompt if the judge is wrong in a consistent direction.
2. From the preview compute the base miss rate `p` and the `unclear` share
   `u`.

## Setting the volume

`min_sessions` comes from the backtest, per side, one-sided 5 percent, 80
percent power, for a detectable rise `d`:

```
n = 2 * (1.645 + 0.84)^2 * p * (1 - p) / d^2
sessions needed per side = n / (1 - u)
```

Reference points at `p = 0.5`: `d = 0.45` needs about 15, `d = 0.32` about
30, `d = 0.25` about 50. Expected choice: about 30 scored sessions per side,
with the daily verdict step from feature 1, roughly two weeks per change at
16 eligible sessions a week. Record the chosen value and the `p`, `u` it came
from in `docs/Living-SOUL.md` and set `improve.minSessions` in the Home
Manager module.

Backfilled sessions may serve as the first baseline only if Hermes ran the
same SOUL over that period; otherwise the first weeks build the baseline.

## Done when

- The backtest has run, 20 rows were reviewed, and `min_sessions` is set from
  measured `p` and `u`.
- `ca soul status` shows verdict counts drawn from outcome labels.
- Both test suites pass.
