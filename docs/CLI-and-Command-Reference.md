# CLI And Command Reference

The pipeline is invoked with `python -m core`.

| Command | Scope | Purpose |
| --- | --- | --- |
| `ingest-corpus` | operational | Normalize configured intake exports into ready JSONL packets. |
| `ask-questions` | profile | Retrieve QMD evidence and synthesize answers with the configured direct LLM. |
| `build-prompts` | profile | Build profile artifacts from the latest QMD answer CSV. |
| `build-skills` | profile | Generate canonical skills from `human_profile.md`. |
| `build-tool-specs` | operational | Generate operational tool specifications. |
| `build-translation-layer` | shared | Generate `INTERACTION_POSTURE.md` and `SOUL.md`. |
| `build-alignment-spec` | shared | Generate the alignment specification. |
| `health-check` | profile | Validate prompts, provider configuration, and QMD availability. |
| `improve-run` | global | Manual TTY route by default: prints `collect samples`, `calculate loss`, `aggregate gradients`, `gradient descent`, then directs review/apply; never applies/deploys. |
| `improve-run --headless` | global | Headless improvement pass: discover/collect/distill/analyze/fold/synthesize into an XDG-state proposal; stdout is exactly one JSON object, no progress (status on stderr). |
| `improve-apply` | global | Review gate for a proposal: the sole writer of experience records. |

There is no `ingest-substrate` or `verify-alignment` command.

## Recursive Improvement (`improve-run` / `improve-apply`)

The CA-native improvement runtime (`improve/`, Node, zero dependencies)
adapts the Backpass backward-pass shape (Backpass MIT (c) 2026 Kun Chen,
https://github.com/kunchenguid/backpass commit
0268201c3896f45d3002de0d439b6cefccb39063 tag backpass-v0.1.32; see
`improve/LICENSE.NOTICE` for adapted source mappings) to one narrow contract: sessions may propose durable
**experience records**, never direct SOUL/memory/skill patches.

Pipeline: `discover` (global transcript stores) -> `collect` -> `distill`
(deterministic) -> `analyze` (acpx only, injectable/mockable) -> `fold`
(deterministic, `minGapEvidence` floor) -> `consolidate` (one judged acpx
call, mechanical merge, fail-soft to lexical) -> `synthesize` (mock
deterministic or production acpx, fail-closed) -> `stage` (deterministic
private staging; synth output is a staged change plan, never final) ->
`measure` (deterministic stable measured IDs/deltas, coverage-or-revert per
measurement) -> `annotate-preface` then `annotate` (fresh logical invocations,
strict final validation, fail-closed) -> proposal (final annotated candidates
only via the terminal review/apply gate).

Analysis prompt (checked in, CA-native): `improve/prompts/analysis.md` audits one distilled personal/coding-agent
trace against the active CA SOUL baseline
(`workspaces/alignment/artifacts/SOUL.md`), the interaction posture
(`workspaces/alignment/artifacts/INTERACTION_POSTURE.md`), and accepted
experience records (`workspaces/experience/authored|staged`). Contract:
strict JSON `{positive, negative, gaps, changed_context,
usedRawTranscript}`; every observation carries a verbatim trace quote;
negatives distinguish current-guidance `non-compliance` from
guidance-caused `harm`; gaps are recurring-use experience-record
candidates, never direct SOUL edits; the raw transcript is out of scope
(`usedRawTranscript` is always false). Rendering lives in the zero-dependency
`improve/src/prompts.js` (Backpass `src/prompts.js` shape): prompts load
relative to the runtime (never CWD), `{{PLACEHOLDER}}` substitution is strict
(missing, unused, and unexpected/non-`UPPER_SNAKE` tokens fail loudly), and
the self-session sentinel `<!-- ca-improve:self-session -->` is prepended
FIRST by the loader, not baked into the file.

Private state (never CA repo state): `$XDG_DATA_HOME/cognitive-assistant/improve/`
(`cursor.json` run state, `evidence/`, `ledger.json` folded ledger,
`proposal.json`, `rejections.jsonl`, plus `prompts/<runId>__<transcriptId>.md`
with a `.json` sidecar naming the run/session relation for every rendered
model prompt, both mode `0600` where supported). Raw transcripts and prompts
never land in git state or the repo -- only the distilled trace travels
inside the rendered prompt in private state. Both `improve-run` routes use the

Supported adapters (global stores, CWD-independent): Hermes
(`~/.hermes/state.db`, read-only), Pi (`~/.pi/agent/sessions`), Claude
Code (`~/.claude/projects`), Codex (`~/.codex/sessions`), OpenCode
(`~/.local/share/opencode/opencode.db`, read-only). Explicitly excluded
in this slice: Grok and Cursor (CLI and IDE) -- their stores are never
read; requesting them is an error. The runtime's own sessions (sentinel
`<!-- ca-improve:self-session -->`, or sessions rooted under its state
dir) are self-excluded before analysis.

Private state (never CA repo state): `$XDG_DATA_HOME/cognitive-assistant/improve/`
(`cursor.json` run state, `evidence/`, `ledger.json` folded ledger,
`proposal.json`, `rejections.jsonl`). Both `improve-run` routes use the
exact existing CA JS pipeline/state/proposal path
(`improve/bin/ca-improve.js run --headless` via `core/improve.py::run_headless`)
and write only there: they never modify tracked files, never apply, and
never touch live Hermes (stores are opened read-only; nothing is deployed).
Default `improve-run` (manual/TTY route) prints exactly `collect samples`,
`calculate loss`, `aggregate gradients`, `gradient descent`, then directs
review with `improve-apply`. `improve-run --headless` prints exactly one JSON
proposal object on stdout with no progress; status goes to stderr only.

`improve-apply` is the sole gate. It refuses a missing proposal
(`improve-run` first) or an unreviewed one (every edit needs an explicit
`accepted` / `rejected[:reason]` decision, via `--decisions` or the
minimal terminal review). Acceptance atomically writes only the approved
experience authored source (`workspaces/experience/authored/<id>.md`) and
the staged generated artifact (`workspaces/experience/staged/<id>.md`);
rejections are recorded in state. It never deploys to Hermes and never
patches SOUL -- SOUL stays the read-only baseline, while
`core/experience.py::compile_experience_block` (hooked into
`prompt_creator.load_dataset_context`) compiles accepted staged
experience into downstream builds.

The Nix flake exposes `ca-improve` (headless package) and
`nixosModules.ca-improve` (systemd **user** service + timer running the
headless pass weekly; applying stays manual).

## Consolidation contract (`improve/prompts/consolidate.md`)

Adapted from the Backpass operational source
(`src/prompts/consolidate.md` at commit 0268201; see
`improve/LICENSE.NOTICE`): one bounded acpx-only call sees the full open gap
set and merges entries that describe the same underlying gap. Runs only when
`>=2` eligible/open gaps exist; otherwise the run keeps deterministic lexical
identity with a visible note and makes no model call. The mock analyzer never
calls acpx here. The rendered prompt is persisted privately as
`prompts/<runId>__consolidate.md` plus a `.json` sidecar carrying run/stage
identifying metadata (`runId`, `stage: consolidate`), both `0600` where
supported. The model returns `{"merges": [[ids], ...]}`; parsing validates
strictly (existing IDs only, `>=2` distinct IDs per group, unique membership
across groups; malformed groups and unknown IDs are dropped, shrinking a
group below two drops it). The merge itself is mechanical: union distinct
session sources (never double-count a session), preserve per-source quote
provenance, keep the shortest instruction as canonical, and re-check the
`minGapEvidence` floor. acpx failure or invalid output degrades to the
deterministic lexical current result with a visible proposal/run note
(`proposal.notes` + `proposal.consolidation.note`); it never aborts the run.

## Synthesis contract (`improve/prompts/synthesis.md`)

Adapted from the Backpass operational sources (`src/prompts/synthesis.md` +
`src/prompts/annotate.md` at commit 0268201; see `improve/LICENSE.NOTICE`)
but CA-native: the model proposes narrow private staged change plans only
(`clusterId` + untrusted `provisionalIntent` + `provisionalSources` with
`>=2` distinct eligible sessions), never final `title`/`body`/`evidence`/
quote mappings/`counterevidence`/`compilerImplication`/staged artifact/diff.
Annotation is the sole full-record author; staged plans carry no
record/evidence. The prompt states explicitly: change only the plan -- never live
files, tracked files, SOUL, posture, skills, or Hermes -- and the plan is
not authoritative pre-apply (the terminal review/apply gate consumes only
annotated finals). Production runs are acpx-only with strict plan validation
(eligible folded cluster; `>=2` distinct eligible sessions; any final field
present is invalid and dropped). The mock path is deterministic
`synthesizePlans` with no real calls, still reviewable. Production failure
(acpx error or zero valid plans) fails closed: no plans plus a visible
proposal note (`proposal.notes` +
`proposal.synthesis.note`). Prior rejections (`state/rejections.jsonl`) render
into `{{REJECTIONS}}`; synthesis itself does not suppress -- suppression
applies downstream on annotated finals unless the final carries higher
evidence (more distinct sessions) or genuinely new evidence (an unseen session
id). The rendered synthesis prompt is persisted privately as
`prompts/<runId>__synthesis.md` plus a `.json` sidecar (`stage: synthesis`),
both `0600` where supported.

## Annotate-preface contract (`improve/prompts/annotate-preface.md`)

CA-native preface with no direct Backpass counterpart (see
`improve/LICENSE.NOTICE`), one of five prompt roles (`analysis`,
`consolidate`, `synthesis`, `annotate-preface`, `annotate`): it frames the
narrow private staged change plans (with measured plan context from
deterministic stage/measure) that already exist
and opens the fresh logical annotate session. Placeholders `{{COUNT}}`,
`{{STAGED_SUMMARY}}`, `{{RUN_ID}}` render the staged-existing set through the
existing strict loader/renderer (`improve/src/prompts.js`), sentinel FIRST and
never baked into the file. The preface outcome is revert-only readiness
metadata (`{"ready": true}`): it never annotates, never authors
records/evidence, and never edits live files,
tracked files, SOUL, posture, skills, or Hermes. An empty staged set stays
sequenced as annotate-preface then annotate. Rendered as
`prompts/<runId>__annotate-preface.md` plus a `.json` sidecar
(`stage: annotate-preface`), both `0600` where supported.

## Annotate contract (`improve/prompts/annotate.md`)

Adapted from the Backpass operational source (`src/prompts/annotate.md` at
commit 0268201; see `improve/LICENSE.NOTICE`) but CA-native: strict JSON
annotations over the narrow private staged change plans with measured plan
context. Each staged plan gets exactly one
annotation -- coverage (`keep`/`drop`) or explicit `revert` when measurement
does not support it. Annotation is the sole full durable-record author: every
`keep` authors the complete record (`title`, `body` at most 2000 chars,
`clusterId`, `sources` with `>=2` distinct sessions, exact session-bound
verbatim `evidence`, `counterevidence` or literal `none observed`,
`compilerImplication`), resting on exact source quote/session binding
(a verbatim `text` quote copied exactly from the staged eligible evidence rows
with its `source` session id; paraphrases and swapped sessions fail), plus required
`counterevidence` (strongest contrary observation or literal `none observed`)
and `compilerImplication` on the staged record. Prohibited operations are
explicit: never live files, tracked files, SOUL, posture, skills, or Hermes;
the proposal stays non-authoritative until the human apply gate consumes only
annotated finals. Production is acpx-only with strict final validation and
fail-closed (staging marked via `staging/annotate.failed`,
candidates cleared, no final proposal edits); the mock path is deterministic
final annotation with no real calls, still reviewable. The terminal
review/apply gate consumes only final annotated candidates. Placeholders `{{COUNT}}`,
`{{STAGED_CANDIDATES}}`, `{{RUN_ID}}` render through the existing strict
loader/renderer, sentinel FIRST. Rendered as
`prompts/<runId>__annotate.md` plus a `.json` sidecar (`stage: annotate`),
both `0600` where supported. All five prompt roles (`analysis`,
`consolidate`, `synthesis`, `annotate-preface`, `annotate`) load via
`improve/src/prompts.js` with strict `{{PLACEHOLDER}}` substitution.
