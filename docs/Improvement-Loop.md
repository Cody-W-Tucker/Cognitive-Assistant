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
- `improve/` (Node, zero dependencies) does discovery, analysis and proposal.
  `improve/bin/ca-improve.js` has two commands, `run` and `synthesize`; both
  print exactly one JSON proposal on stdout. Progress (`--tui`) and errors go
  to stderr. `run` and `synthesize` share the tail in `src/propose.js`.

The runtime writes only under its state directory. Session stores are opened
read-only, and nothing in the repo or in Hermes is modified.

## Stages of `improve-run`

| Stage | Module | Model call |
| --- | --- | --- |
| discover | `src/harnesses.js` | no |
| collect + distill | `src/distill.js` | no |
| analyze | `src/analyze.js`, `prompts/analysis.md` | one per session |
| fold | `src/fold.js` | no |
| consolidate | `src/consolidate.js`, `prompts/consolidate.md` | one, only with >= 2 gaps |
| synthesize | `src/synthesize.js`, `prompts/synthesis.md` | one |
| annotate | `src/annotate.js`, `prompts/annotate.md` | one |
| propose | `src/propose.js` | no |

- **Discover.** Lists sessions from each harness store (below), skipping
  sessions older than `--since`, sessions the cursor already processed at the
  same revision, and the runtime's own sessions (marked with
  `<!-- ca-improve:self-session -->` or rooted under the state directory).
- **Distill.** Deterministically keeps user and assistant messages plus
  one-line tool shapes and drops boilerplate.
- **Analyze.** Audits each distilled session against the running SOUL, the
  interaction posture and the active records from `experience-context.md`
  (each context is cut to 6000 characters). The reply is strict JSON:
  `positive`, `negative` (each tagged `non-compliance` with current guidance or
  `harm` caused by it), `gaps` and `changed_context`, every observation backed
  by a verbatim quote. A failure is recorded for that session and retried on a
  later run; earlier good evidence is never overwritten by a failure.
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
  evidence item an exact quote from its own session, counterevidence (or
  `none observed`) and a compiler implication. Any invalid kept record fails
  the whole annotation, leaving the proposal with no edits and a note.
- **Propose.** Drops records whose cluster or title was rejected before
  unless they now cite more sessions or a session the rejection did not, then
  writes `proposal.json`. An unapplied proposal it replaces is archived to
  `proposals/<id>.json`.

Each edit in the proposal is `{id, kind: "add", title, rationale, evidence,
record, annotation: {verdict: "keep", reason}, clusterId}`. The proposal also
records the SOUL it was made against (`soul: {path, sha256, chars}`), stats
and any stage notes.

`improve-synthesize` re-runs only consolidate -> synthesize -> annotate ->
propose over `evidence/` and `ledger.json` already on disk (`src/resume.js`).
It fails with a message naming the fix when there is no successful evidence,
no ledger, a corrupt ledger, no eligible cluster, or no configured model
endpoint.

## Harnesses

| Harness | Store |
| --- | --- |
| `hermes` | `$HERMES_HOME/state.db` (default `~/.hermes/state.db`) |
| `claude` | `~/.claude/projects`, plus `$CLAUDE_CONFIG_DIR/projects` |
| `codex` | `$CODEX_HOME/sessions` (default `~/.codex/sessions`); rollout JSONL whose lines are wrapped as `{type, payload}` |
| `opencode` | `~/.local/share/opencode/opencode.db`, sessions read via `opencode export` |

Each adapter in `src/harnesses.js` both lists sessions and reads one. Without
`--harness` every store is scanned and missing ones are skipped; a harness
named with `--harness` must be readable or the run fails. Pi, Grok and Cursor
are deliberately excluded and naming them is an error. With
`CA_IMPROVE_HOME` (Python) / `--home` (runtime) every store is looked up under
that one directory and the ambient `HERMES_HOME` etc. are ignored.

Tuning: `CA_IMPROVE_JOBS` (parallel sessions, default 4),
`CA_IMPROVE_MAX_OPENCODE_EXPORTS` (newest OpenCode sessions per run, default
50), `CA_IMPROVE_OPENCODE_BIN` (default `opencode`).

## Model calls

Every model call is one tool-free, OpenAI-compatible chat completion made in
process by `src/model.js`. The model gets no tools, workspace or shell; its
reply is parsed only as one JSON object and validated by the stage that asked
for it, and code decides every path and field that is written.

| Variable | Meaning |
| --- | --- |
| `CA_LLM_BASE_URL` | Endpoint base, e.g. `http://127.0.0.1:8080/v1` (required) |
| `CA_LLM_MODEL` | Model for every role |
| `CA_LLM_MODEL_<ROLE>` | Per-role override: `ANALYSIS`, `CONSOLIDATE`, `SYNTHESIS`, `ANNOTATE` |
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
