# Improvement Loop

The improvement loop reads the agent's real sessions and proposes small,
evidence-backed **experience records**. It never patches the SOUL, skills,
memory or Hermes directly: an accepted record is written to the lineage and
the living SOUL is recompiled from it (see [Living SOUL](Living-SOUL.md)).

```text
improve-run  ->  <CA home>/improve/proposal.json  ->  improve-apply  ->  experience/authored/<id>.md
                                                                     ->  soul compile (new generation)
```

## Who does what

- `core/improve.py` (Python) launches the runtime, applies reviewed decisions
  and runs the `--auto` cycle. It passes the runtime its state directory
  (`<CA home>/improve`), the SOUL Hermes is running (the living SOUL once
  compiled, else the bootstrap), the interaction posture, and
  `--experience-file <CA home>/improve/experience-context.md`. Python rewrites
  that file before each run with the *active* records (not withdrawn, not
  absorbed by the bootstrap), so the runtime never reads the
  `experience/authored/` layout itself. `node` must be on `PATH` (the dev
  shell and the `ca` package provide it).
- `improve/` (Node, zero dependencies) does discovery, analysis, outcome scoring
  and proposal. `improve/bin/ca-improve.js` has three commands, `run`,
  `synthesize` and `outcome`: `run` prints exactly one JSON proposal on
  stdout, `outcome` prints the `{runId, preview, selected, scored,
  unscored}` summary. Progress (`--tui`) and errors go to stderr. `run` and
  `synthesize` share the tail in `src/propose.js`; `run` also scores mature
  sessions in-process via `src/outcome.js` before proposing (see [Delayed
  outcome scoring](#delayed-outcome-scoring)).

The runtime writes only under its state directory. Session stores are opened
read-only, and nothing in the repo or in Hermes is modified.

## Stages of `improve-run`

| Stage | Module | Model call |
| --- | --- | --- |
| discover | `src/harnesses.js` | no |
| collect + distill | `src/distill.js` | no |
| analyze | `src/analyze.js`, `prompts/analysis.md` | one per session |
| outcome | `src/outcome.js`, `src/followup.js`, `prompts/outcome.md` | one per mature session |
| fold | `src/fold.js` | no |
| consolidate | `src/consolidate.js`, `prompts/consolidate.md` | one, only with >= 2 gaps |
| synthesize | `src/synthesize.js`, `prompts/synthesis.md` | one |
| annotate | `src/annotate.js`, `prompts/annotate.md` | one |
| propose | `src/propose.js` | no |

- **Discover.** Lists sessions from Langfuse (below), skipping sessions whose
  turns all started before `--since`, sessions still active within
  `--idle-hours`, sessions the cursor already processed at the same last
  activity, and the runtime's own sessions (marked with
  `<!-- ca-improve:self-session -->` in the first user message, or a Claude
  cwd under the state directory).
- **Distill.** Deterministically keeps user and assistant messages plus
  one-line tool shapes and drops boilerplate.
- **Analyze.** Audits each distilled session against the running SOUL, the
  interaction posture and the active records from `experience-context.md`
  (each context is cut to 6000 characters). The prompt requests `positive`,
  `negative` (tagged `non-compliance` with current guidance or `harm` caused
  by it), `gaps` and `changed_context`, with verbatim quotes. The runtime
  checks and persists the first three arrays, not `changed_context`; it does
  not verify analysis quotes against the transcript. A failure is recorded
  for that session and retried on a later run; earlier good evidence is never
  overwritten by a failure.
- **Fold.** Clusters near-duplicate gaps across sessions; a cluster is
  eligible once `--min-gap-evidence` distinct sessions support it.
- **Consolidate.** One call groups paraphrases of the same gap; the merge
  itself is mechanical. Gaps seen once persist in `open-gaps.json` so they can
  reach the floor over several runs. A failed or invalid reply falls back to
  exact matching with a note on the proposal.
- **Synthesize.** One call returns at most 16 *plans*: an eligible cluster, a
  provisional intent and the sessions behind it. Plans carry no record text,
  quotes or file paths. Past rejections are shown to the model.
- **Annotate.** One call gives every plan a verdict `keep`, `drop` or
  `revert`. A `keep` must author the complete record, which is validated
  against the ledger: id `exp-<slug>-<12-char hash>`, title, body of at most
  2000 characters, at least two distinct sessions from that cluster, every
  evidence item an exact match to an analysis quote attributed to its own
  session, counterevidence (or `none observed`) and a compiler implication.
  Any invalid kept record fails the whole annotation, leaving the proposal
  with no edits and a note.
- **Propose.** Drops records whose cluster or title was rejected before
  unless they now cite more sessions or a session the rejection did not, then
  writes `proposal.json`. An unapplied proposal it replaces is archived to
  `proposals/<id>.json`.

Discovery skips an unfinished Hermes session until it has ended or been idle
for 12 hours (`--idle-hours`), without advancing the cursor, and a session with
successful evidence is never analyzed again. The session list is filtered
before any messages are read, so a run reads the transcripts of new sessions,
not of the whole store. Distillation keeps the head and the tail of a long
trace around an elision marker, and includes Hermes tool calls.

Evidence carries `sessionAt` (session start), `startedAt`, `endedAt`,
`source`, `cwd`, `gitRepoRoot` and `parentSessionId`, plus
`rubric: {promptSha, contextSha, model}`. `endedAt` is the session's last
activity when the store records it: Hermes stamps `ended_at` when it reaps an
idle session, which can be weeks after the person stopped. `cwd` and
`gitRepoRoot` are optional; most Hermes sessions have neither. The prompt hash identifies the
analysis template; the context hash identifies rendered SOUL, posture and
records contexts. Older evidence may lack these fields. See
[Living SOUL](Living-SOUL.md#outcome-check-and-autonomous-changes) for how
missing sources and rubric stamps affect verdicts.

Each edit in the proposal is `{id, kind: "add", title, rationale, evidence,
record, annotation: {verdict: "keep", reason}, clusterId}`. The proposal also
records the SOUL it was made against (`soul: {path, sha256, chars}`), stats
and any stage notes.

`improve-synthesize` re-runs only consolidate -> synthesize -> annotate ->
propose over `evidence/` and `ledger.json` already on disk (`src/resume.js`).
It fails with a message naming the fix when there is no successful evidence,
no ledger, a corrupt ledger, no eligible cluster, or no configured model
endpoint.

## Sessions come from Langfuse

The runtime reads every session from the Langfuse public API
(`src/langfuse.js`, `/api/public/v2/observations` with cursor paging and
retries on 429/5xx), never from harness stores on disk, so it works from any
machine. It needs `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and
`LANGFUSE_BASE_URL`; without them, or when Langfuse is unreachable, the run
fails rather than reporting no sessions.

Each harness traces one root observation per turn, and a session is the set of
roots sharing a `sessionId`:

| Harness | Root observation | Session metadata kept |
| --- | --- | --- |
| `hermes` | `Hermes turn` | `metadata.platform` as the session source (desktop, tui, cli, telegram, cron, subagent, ...) |
| `claude` | `Conversational Turn` with `metadata.source=claude-code` | `metadata.cwd` |
| `opencode` | `opencode.turn` | none |

`src/harnesses.js` turns one session's observations into events: each turn's
user text at its start, its `TOOL` observations as they started, and its
assistant text at its end. A session's revision is a hash of its ordered root
ids and end times; outcome scoring uses it to check a session has not changed
since its snapshot was cut. Langfuse records no session end, so a session is
finished once it has been idle for `--idle-hours` (default 12), for every
harness.

Left out: Langfuse evaluator runs (environment `langfuse-llm-as-a-judge`),
Pi turns (`Conversational Turn` with `source=pi`), and OpenCode subagent
sessions (their turns are nested in the parent's trace, not roots). Codex is
not traced and is not supported; Pi, Codex, Grok and Cursor are rejected by
name. Hermes traces are captured `sanitized` and Claude traces may carry
truncation markers, so a trace can hold less text than the harness's own
store did. Nothing before Langfuse tracing began (mid-September 2026) is
reachable.

`--max-sessions N` bounds one run's model work: at most N sessions are
analyzed and at most N mature sessions are outcome-scored. Hermes sessions go
first, since verdicts are judged on them, then the newest; the rest stay
uncheckpointed and wait for a later run (a backlog older than `--since` is
never reached).

Tuning: `CA_IMPROVE_JOBS` (parallel sessions, default 4).

## Model calls

Every model call is one tool-free, OpenAI-compatible chat completion made in
process by `src/model.js`. The model gets no tools, workspace or shell; its
reply is parsed as JSON data and validated by the stage that asked for it,
and code decides every path and field that is written. Synthesis requires
an exact JSON object (including cached replies); other roles can recover an
object from a code fence or surrounding prose.

| Variable | Meaning |
| --- | --- |
| `CA_LLM_BASE_URL` | Endpoint base, e.g. `http://127.0.0.1:8080/v1` (required) |
| `CA_LLM_MODEL` | Model for every role |
| `CA_LLM_MODEL_<ROLE>` | Per-role override: `ANALYSIS`, `CONSOLIDATE`, `SYNTHESIS`, `ANNOTATE`, `OUTCOME` |
| `CA_LLM_API_KEY_FILE` | Optional file with a bearer key (use an inference-only key) |
| `CA_LLM_RETRY_DELAYS_MS` | Backoff for 429, 5xx and network errors (default `5000,20000`) |

Requests use temperature 0, seed 0 and JSON-only output. Each parseable reply
is cached in `model-cache/<sha256 of request>.txt`, so an unchanged prompt is
not sent twice. `improve-run --analyzer model` checks this configuration before
analyzing anything and fails if a role has no endpoint or model.
`--analyzer mock` (`src/mock.js`) makes no calls and is what the tests use.

Every rendered prompt is archived as `prompts/<runId>__<name>.md` with a
`.json` sidecar, mode 0600. Prompts are rendered by `src/prompts.js` with
strict `{{UPPER_SNAKE}}` placeholders (missing or unexpected ones fail), and
the self-session sentinel is prepended so the runtime never analyzes its own
calls.

## Review and apply

`improve-apply` is the only writer of experience records.

- It refuses when there is no proposal, the proposal was already applied, or
  `--proposal` does not match the id on disk (a newer run replaced the one you
  reviewed).
- Every edit needs a decision, and only edits whose annotation verdict is
  `keep` with a complete record can be accepted. Without `--decisions` each
  candidate is printed in full and you answer accept/reject in the terminal.
- Accepted records go to `<CA home>/experience/authored/<id>.md` (front
  matter `id`, `title`, `sources`, `cluster`, `proposal`, `created`; then the
  body, evidence, counterevidence and compiler implication). Rejections are
  appended to `improve/rejections.jsonl`, and the proposal is marked
  applied. If any write fails, every file touched is restored. A second
  concurrent apply fails on `improve/.apply.lock`.
- If anything was accepted, the living SOUL is recompiled into a new
  generation.

The `--auto` cycle calls the same apply with one edit `accepted` and the rest
`deferred`; deferred edits are neither written nor rejected, so a later run
can propose them again. See [Living SOUL](Living-SOUL.md) for how changes are
judged and reverted.

## Journal

`core/journal.py` keeps a private, append-only history at
`<CA home>/improve/journal/events.jsonl` (directory 0700, files 0600). Event
types: `run_completed`, `proposal_created`, `experience_accepted`,
`proposal_rejected`, `soul_compiled`, `soul_rolled_back`, `soul_verdict`,
`auto_cycle` (`artifact_compiled` is still readable from older journals but no
longer written). Every event is checked before it is written: transcripts,
prompts, quotes, record bodies, SOUL text, credentials and absolute paths are
rejected; sources appear only as short id refs. `python -m core
journal-compact` regenerates the views `current.json` and `bootstrap.md` and
tolerates missing or malformed lines. The journal never deletes anything
outside `journal/`.

## Provenance

Several runtime modules adapt Backpass (MIT, Kun Chen, commit 0268201). The
per-file mapping and license text are in `improve/LICENSE.NOTICE`.

### Delayed outcome scoring

After analysis, the runtime scores each mature session that has successful
evidence, once, with a blind outcome prompt: the judge sees the session trace
and follow-up evidence, never the SOUL, posture or records. A session is mature
three days after it ended (`--mature-days`). The label is one of `advanced`,
`stalled`, `regressed`, `answered` (a question the reply itself settled, so
nothing afterwards can show more) or `unclear`. Citations and verbatim quotes
are checked before an outcome is written; `answered` and `unclear` need none. The analyzer's positive, negative and
gaps are not touched.

Follow-up evidence is whatever falls inside the window after the session
ended:

- **Later sessions.** Every later Hermes session from the `desktop`, `tui` or
  `cli` sources that is not a continuation of another, with no directory
  requirement; the judge decides whether one is about the same aim. Sessions
  from other harnesses are matched by repository or directory, which in
  Langfuse only Claude sessions record, so later OpenCode sessions are not
  found (commits still are, through touched paths). The earliest
  eight are kept, each as its first user message and last agent message.
- **Commits.** `git log` in the session's repository when it records one, and
  in up to four repositories its tool calls touched (absolute paths in file
  arguments and shell commands). Most Hermes sessions record no directory, so
  the second is what usually finds them. Each commit carries its `repo`; the
  judge counts one only when its subject is about the same aim.
- **Journal.** A keyword `qmd` search of the `Journal` collection, limited to
  notes dated inside the window. This rarely matches; see
  `plans/feature-2.md`.

The trace is a snapshot taken when the session was analyzed, used only while
the session's transcript is unchanged since. For SQLite stores the revision
covers that session's messages, not its session row or the rest of the
database, so Hermes reaping an idle session does not invalidate it; new
messages do. Header-only OpenCode exports cannot be verified and are excluded.

A session that cannot be scored (no known end, a changed transcript, an
invalid reply, a model error) is left without an outcome. Nothing is written
for it, the run continues, a later run tries again, and verdicts ignore it.
`improve-outcome` reports how many were `scored` and `unscored`.

`CA_LLM_MODEL_OUTCOME` overrides `CA_LLM_MODEL` for this tool-free role.

**Backtest.** `python -m core improve-outcome --since 70d --dry-run` writes a
private JSONL preview under `<CA home>/improve/outcome-preview/` and changes
no evidence. A dry run also previews finished Hermes sessions that were never
analyzed, from every source, reading their transcripts as they stand, so it
works on a fresh CA home. Each row is `{harness, transcriptId, source,
startedAt, endedAt, followup: {sessions, commits, journal}, outcome}`, where
`followup` holds counts and `outcome` is `{aim, label, reason, evidence,
rubric, scoredAt}`. `--limit N`, `--mature-days N`, `--rescore` and
`--analyzer mock` are also available.

Rescoring existing outcomes requires `--rescore`; use it deliberately after a
rubric change. Preview and cache files contain private session material.
