# Feature 1: make the measurement valid

Goal reference: `IDEA.md`. This is credit assignment and evaluation hygiene.
It adds no new signal. It makes every session count for the generation that
produced it, makes both sides of a verdict comparable, and lets the judge see
the whole session. Feature 2 depends on it.

File and line references come from a read-only audit on 2026-11-14 and may
have shifted; confirm each before editing.

## Why

- Sessions are attributed by last activity, and still-open sessions are
  re-analyzed every run and moved to the newest generation. In the live
  Hermes store every telegram (122) and discord (22) session is open-ended.
- The two sides of a verdict are scored against different SOUL and record
  text, and nothing on the evidence says which.
- Distill keeps only the first 24000 characters, so the end of a session,
  where the outcome shows, is cut. Hermes tool calls are dropped.
- cron, api_server and subagent sessions enter the miss rate.

## Scope

### Required

1. **Attribute by start time.**
   - `improve/src/harnesses.js` (Hermes list, around 204-207 and 251-252):
     carry both `startedAtMs` and `mtimeMs` on each discovered transcript.
     Keep `mtimeMs` for the cursor; use `startedAtMs` for attribution.
   - `improve/src/pipeline.js` (around 137): write `sessionAt` from
     `startedAtMs`, and also persist `endedAt`.
   - claude/codex: use the first event timestamp when present, else mtime.

2. **Analyze only finished sessions.**
   - A Hermes session is eligible when `ended_at` is set, or when it has been
     idle longer than `--idle-hours` (default 12).
   - Ineligible sessions are skipped without advancing the cursor.
   - Once a session has `status: ok` evidence, a later mtime change does not
     re-queue it. Sessions are scored once.

3. **Source allowlist for verdicts.**
   - Persist the Hermes `source` on the evidence.
   - `core/outcome.py` `session_outcomes`: count only sources in the policy
     allowlist. Default: `desktop`, `tui`, `cli`.
   - Other sources are still analyzed (they can produce gaps) but never count
     in a verdict.

4. **Fix the Hermes reader** (`improve/src/harnesses.js`, around 264-268).
   - Read only `active = 1` messages when the column exists.
   - Map `tool_calls` / `tool_name` into tool events; a `role = 'tool'` row is
     tool output, not tool input.
   - Drop `role = 'session_meta'` rows instead of treating them as user turns.

5. **Distill keeps head and tail.**
   - `improve/src/distill.js` (around 108): replace `.slice(0, 24000)` with a
     head-plus-tail cut and an explicit elision marker, the same way
     `clampMessage` does for a single message.

6. **Stamp the evidence.**
   - `improve/src/pipeline.js`: add
     `rubric: {promptSha, contextSha, model}` to each evidence record.
     `promptSha` is the sha256 of the analysis template, `contextSha` of the
     rendered SOUL + posture + records contexts.
   - `core/outcome.py`: if the two sides of a comparison hold evidence with
     different `promptSha` or `model`, return `pending` with a reason naming
     the mismatch. Evidence without a stamp is treated as its own rubric.

7. **Persist session metadata feature 2 needs.**
   - Add to evidence: `cwd`, `gitRepoRoot`, `startedAt`, `endedAt`, `source`,
     `parentSessionId` (null when the store does not have them).
   - Key evidence files by `harness:id`, not by `transcriptId` alone
     (`improve/src/state.js`, around 54-56). Read old-style names as a
     fallback so existing state is not orphaned.

### Can defer until after the backtest

8. **Content-hash generations.** `core/living_soul.py` (around 173-193):
   when the compiled text matches any earlier generation's sha256, reuse that
   generation instead of minting a new number, so its sessions remain the
   baseline. `core/outcome.py` `evaluate`: when the current generation added
   nothing and its parent has no verdict, judge the parent.

9. **One policy object and a cheap verdict step.**
   - `core/outcome.py`: `OutcomePolicy(min_sessions, z_threshold, harness,
     sources)`, read by `evaluate` and `improve.auto_cycle`. Remove the
     duplicated defaults in `core/improve.py` and `core/cli.py`.
   - CLI: `ca soul verdict` runs only the outcome check and any resulting
     revert or adopt, without analysis. Add `--z-threshold`.
   - `flake.nix`: a second timer for the verdict step (daily); the analysis
     timer stays as configured.
   - Compute `session_outcomes` once per auto cycle and pass it down.

10. **SQL pushdown.** `harnesses.js` (around 204, 256): apply `--since` in
    the query and fetch first-message text only for candidate sessions.

## Out of scope

- Any change to what counts as a miss (feature 2).
- The bootstrap pipeline, the journal, the Langfuse review queue.
- Testing more than one change at a time.

## Tests

- Node (`improve/tests/`): start-time attribution; an open session is skipped
  and not cursored; a scored session is not re-queued; Hermes reader handles
  `active`, `tool_calls`, `session_meta`; distill keeps the tail; evidence
  carries `rubric` and metadata; legacy evidence file names still load.
- Python (`tests/test_outcome.py`): source allowlist; rubric mismatch gives
  `pending`. The existing test that locks verdicts to `harness="hermes"`
  moves to the policy default.
- Both suites pass:
  `nix develop --command python -m unittest discover -s tests -v` and
  `nix develop --command bash -c 'cd improve && npm test'`.

## Docs

Update `docs/Improvement-Loop.md` (discover, distill, evidence fields) and
`docs/Living-SOUL.md` (attribution, source allowlist, the "same prompt"
claim). Keep ASCII where `tests/test_ascii.py` requires it.

## Done when

- A dry run against the live Hermes store (`--analyzer mock`) lists only
  finished sessions, and its evidence shows `sessionAt` equal to the session
  start, a `source`, and a `rubric` stamp.
- No evidence file changes generation between two consecutive runs.
- Both test suites pass.
