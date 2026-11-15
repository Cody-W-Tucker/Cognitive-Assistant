# Feature 4: Read sessions from the Langfuse API instead of local harness stores

Status: implemented 2026-11-14 (local adapters deleted, Codex dropped). Not
yet done: the parity gate and the before/after backtest on the Hermes host
(steps 1 and 7), which need that machine.

## Goal

The improvement runtime reads sessions directly from harness stores on disk
(Hermes and OpenCode SQLite, Claude and Codex JSONL). Replace that with the
Langfuse API so the loop has one session source that works from any machine.

## What the probe found

- **Direct reads live in one file.** `improve/src/harnesses.js` holds every
  store reader. Only `pipeline.js`, `outcome.js` and `followup.js` consume it.
- **No sessions endpoint.** `/api/public/sessions` and `/api/public/traces`
  return 404 on this instance, so everything must go through
  `/api/public/v2/observations`. Its `sessionId`, `isRootObservation`, `name`
  and time filters all work, with cursor paging.
- **Three of four harnesses are traced.** Codex is absent.

| Harness | Root observation | Sessions in Langfuse | Since |
|---|---|---|---|
| Hermes | `Hermes turn` | 175 | 2026-09-16 |
| OpenCode | `opencode.turn` | 1,735 | 2026-09-15 |
| Claude | `Conversational Turn` (`metadata.source=claude-code`) | 26 | 2026-11-11 |

- **The dev machine has no local Hermes sessions.** `~/.hermes/state.db`
  there has zero rows, so the loop only sees Hermes sessions when run on the
  Hermes host.
- **Some fields are missing in Langfuse.** There is no `ended_at`, no
  `parent_session_id`, and no cwd or repo root for Hermes and OpenCode. Hermes
  carries `metadata.platform` (desktop, tui, subagent, cron, api_server,
  telegram). Claude carries `metadata.cwd`.
- **Content is not raw.** Hermes traces are `capture_mode=sanitized`, and the
  Claude traces carry truncation markers (`user_text.truncated`,
  `output_meta.truncated`).
- **Other roots to exclude.** Evaluator runs appear as root observations in
  the `langfuse-llm-as-a-judge` environment with no session id. Some
  `Conversational Turn` roots have `metadata.source=pi`, which the runtime
  already excludes by rule.

## Observation shapes seen

| Harness | User text | Assistant text | Tool calls |
|---|---|---|---|
| Hermes | root `input.content[].text` | root `output.content` | `TOOL` observations named `Tool: <name>`, `input` and `output` objects |
| OpenCode | root `input[].content[]` | root `output[].content[]` | `TOOL` observations named by tool, `input` object, `output.content` |
| Claude | root `input.content` | root `output.content` | `TOOL` observations named `Tool: <name>`, `input` object, `output` string |

## Plan

1. **Parity gate, before any code.** On the Hermes host, distill about 20
   sessions from both `state.db` and Langfuse and diff the traces. If
   sanitizing or truncation removes text the analysis or outcome judge quotes,
   fix the capture first.
2. **Add `improve/src/langfuse.js`.** A zero-dependency `fetch` client with
   basic auth, cursor paging and retry on 429/5xx. It uses the same
   `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and `LANGFUSE_BASE_URL`
   variables as `review-queue`. `fetch` is injectable for tests.
3. **Rewrite `harnesses.js` as a Langfuse source with the same exports**
   (`discoverTranscripts`, `readTranscriptEvents`, `transcriptRevision`,
   `sessionEndMs`, `cutoffMs`, `SUPPORTED_HARNESSES`).
   - **Discover:** page root observations in the `--since` window with
     `fields=core,basic,metadata`, drop the `langfuse-llm-as-a-judge`
     environment and `source=pi`, and group by `sessionId`. Harness comes from
     the root observation name.
   - **Session fields:** `startedAtMs` is the first turn's start, `mtimeMs`
     is the last end time, `activityKnown` is true, and `source` is the Hermes
     `platform`. `platform=subagent` stands in for the parent-session check.
     `cwd` is set for Claude only.
   - **Finished sessions:** the existing idle-hours rule becomes the only
     signal, since Langfuse has no `ended_at`.
   - **Read:** fetch one session's observations with `io`, order by start
     time, and normalize the three shapes above into the existing
     `{kind: message|tool}` events.
   - **Revision:** a hash of the ordered observation ids and end times
     replaces the SQLite row hash and the file stat.
   - **Self sessions:** keep the sentinel check on the first root input and
     the `cwd` under state dir check.
4. **Rewire consumers.**
   - Snapshot `location` becomes `{harness, id}` in `outcome.js`.
   - Remove `--home` and the `HERMES_HOME` / `CLAUDE_CONFIG_DIR` /
     `CODEX_HOME` handling from `ca-improve.js`, `pipeline.js` and
     `core/improve.py`.
   - Remove `capOpencode`, `CA_IMPROVE_MAX_OPENCODE_EXPORTS`,
     `CA_IMPROVE_OPENCODE_BIN` and the `opencode export` fallback.
   - `distill` prints `source: <path or db>`; give it a Langfuse session
     reference instead.
5. **Migrate state.**
   - Session ids look unchanged between the stores and Langfuse, so evidence
     and checkpoints should carry over. Confirm on the Hermes host.
   - Checkpointed `mtimeMs` values will differ, so sessions are rediscovered
     once. Existing `status: ok` evidence already stops re-analysis.
   - Pending outcome snapshots hold old-style revisions and locations. Re-cut
     them from Langfuse once; otherwise they stay unscored forever.
6. **Update the edges.**
   - `core/improve.py` fails clearly when the Langfuse variables are missing.
   - The Home Manager module for the daily improvement pass gets an
     environment file for the Langfuse credentials.
   - Update `.env.template`, `AGENTS.md`, `docs/Improvement-Loop.md`,
     `docs/CLI-and-Command-Reference.md` and
     `docs/Workspaces-and-Generated-Artifacts.md`.
7. **Rewrite tests and verify.**
   - `improve/tests/harnesses.test.mjs` and `helpers.mjs` move from fixture
     stores to fixture observation pages served by a fake `fetch`.
   - Adjust the store-dependent cases in `outcome.test.mjs`,
     `followup.test.mjs`, `pipeline.test.mjs`, `cli.test.mjs` and
     `tests/test_improve.py`.
   - Run `improve-outcome --since 70d --dry-run` before and after on the
     Hermes host and compare labels.
   - Run `improve-run --headless --analyzer mock` end to end.

## Risks

- **OpenCode follow-up matching weakens.** Later sessions are matched by repo
  or cwd, which Langfuse lacks for OpenCode. Commits still resolve through
  touched paths. Fixing this means adding cwd to the OpenCode plugin's trace
  metadata.
- **History floor.** Nothing before mid-September 2026 is reachable, which
  just covers the 70-day backtest today.
- **Daily run depends on Langfuse.** If it is unreachable, the run must fail
  loudly, not report "no sessions".
- **Follow-up `source` values.** `followup.js` accepts `desktop`, `tui` and
  `cli`. The probe saw `desktop` and `tui` as platforms but not `cli`; confirm
  how CLI sessions are labelled.

## Open decisions

- **Codex.** Recommended: drop it until it is instrumented, since verdicts
  are judged on Hermes sessions only. The alternative keeps the JSONL reader
  just for Codex, which leaves two session sources.
- **Local adapters.** Recommended: delete them outright (about 400 lines).
  Keeping a fallback path means two paths to keep in parity.

## Out of scope

- `core/ingest_corpus.py` and the operational profile's batch corpus exports.
- `core/langfuse_review.py` and the review queue; it keeps its own Python
  client.
