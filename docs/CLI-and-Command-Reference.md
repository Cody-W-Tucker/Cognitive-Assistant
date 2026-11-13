# CLI and Command Reference

Entry point: `python -m core [--profile <name>] <command>` (the `ca` Nix
package is the same CLI). `python -m core <command> --help` prints the flags.
The parser lives in `core/cli.py`.

Stages check their requirements before doing anything: a missing API key,
input file or unsupported profile prints `Error: <command>: configuration
issues found` with the list, and exits 1. A stage that fails while running
prints `Error: <command>: <reason>` and exits 1.

## Profile stages (need `--profile`)

| Command | Reads | Writes |
| --- | --- | --- |
| `ingest-corpus` | `workspaces/<p>/data/intake/` | `workspaces/<p>/data/ready/<source>/*.jsonl`, `ready/preprocessing_manifest_<ts>.json` |
| `ask-questions` | `profiles/<p>/questions.csv`, QMD collections | `workspaces/<p>/data/questions_with_answers_qmd_<ts>.csv` |
| `build-prompts` | newest answers CSV | `workspaces/<p>/artifacts/human_profile.md`, `profile_candidate_<provider>.md` |
| `build-skills [--bio PATH]` | `human_profile.md` (or `--bio`), existing skills | `workspaces/skills/<p>/<slug>/SKILL.md` |
| `build-tool-specs [--bio PATH]` | `human_profile.md`, seed specs in `profiles/<p>/prompts/` | `workspaces/<p>/artifacts/tool_specs/*.md` |
| `health-check` | prompts, questions, environment | nothing |

- `ingest-corpus` is only enabled for profiles with `has_corpus_ingest`
  (operational); `build-tool-specs` only for profiles with `supported_tools`
  (operational). Other profiles get a configuration error, never a silent
  no-op.
- `ask-questions` fails closed: if QMD is missing, returns nothing, or reports
  an index older than 14 days or a missing collection, the run stops before
  calling a model. Questions whose model call fails three times stay empty and
  the command exits 1 after saving what it answered.
- `build-prompts` sends the same prompt to xAI, Anthropic and OpenAI, keeps
  each draft as `profile_candidate_<provider>.md`, and has Anthropic merge them
  into `human_profile.md`.
- `build-skills` creates each skill the profile declares on first build and
  refines the existing `SKILL.md` afterwards. It then deletes any directory in
  `workspaces/skills/<p>/` that the profile does not declare; other groups are
  never touched. See [Skills System](Skills-System.md).
- `build-tool-specs` expects exactly the declared tool files back, each with
  `## Mission`, `## Use This Tool For`, `## Decision Rules` and `## Avoid`;
  spec files no longer declared are removed.

## Cross-profile commands

| Command | What it does |
| --- | --- |
| `list-profiles` | Print registered profile names |
| `build-translation-layer` | Build `INTERACTION_POSTURE.md`, then the bootstrap `SOUL.md` from both human profiles plus the runtime lineage, and write `absorbed.json`. See [Alignment Artifacts](Alignment-Artifacts.md) |
| `build-alignment-spec` | Build `alignment_spec.md` from every skill in the store |
| `update [--skip-tool-specs]` | For `--profile` (or every profile): `build-prompts`, `build-skills`, `build-tool-specs` when supported; then `build-translation-layer` and `build-alignment-spec`. Stops at the first failure |
| `enhance-skill [--skill SLUG] [--hermes-path PATH] [--apply]` | Compare store skills with newer Hermes copies, preview the diff, and with `--apply` merge them with a model call |
| `review-queue [--dry-run]` | Refill the Langfuse review queue. See [Projection Experiments](Projection-Experiments.md) |

Output paths for the cross-profile stages are fixed in `core/paths.py`; there
are no `--output` or `--seed-dir` flags.

## Improvement loop and living SOUL

Runtime state lives under CA home (`$CA_HOME`, default
`$XDG_DATA_HOME/cognitive-assistant`); commands also read bootstrap artifacts
and session stores, and `soul link` writes the Hermes SOUL symlink. There are
no `--state-dir` or `--soul-path` flags. Details:
[Improvement Loop](Improvement-Loop.md) and [Living SOUL](Living-SOUL.md).

`improve-run` flags:

| Flag | Default | Meaning |
| --- | --- | --- |
| `--headless` | off | Print exactly one JSON proposal on stdout; without it the run needs a TTY and shows live progress on stderr |
| `--since` | `30d` | Only sessions newer than this (`12h`, `2w`, `all`) |
| `--analyzer` | `model` | `model` (configured endpoint) or `mock` (no model calls) |
| `--min-gap-evidence` | `2` | Distinct sessions a gap needs before it can become a candidate (integer >= 2) |
| `--harness NAME` | all | Scan only this harness (repeatable); a named harness whose store is missing fails the run |
| `--auto` | off | With `--headless`: judge the change under test, then revert, wait, or adopt one record |
| `--min-sessions` | `15` | `--auto`: analyzed sessions needed on each side before judging |

`CA_IMPROVE_HOME`, when set, scopes every session store under that one home
directory (used for hermetic runs).

| Command | What it does |
| --- | --- |
| `improve-synthesize [--min-gap-evidence N]` | Propose again from saved evidence and ledger; no discovery or analysis |
| `improve-apply [--proposal ID --decisions "e1=accepted e2=rejected:too-narrow"] [--dry-run]` | Review the current proposal: write accepted records, log rejections, compile the living SOUL. Without `--decisions` it asks in the terminal |
| `journal-compact` | Rebuild `journal/current.json` and `journal/bootstrap.md` from `events.jsonl` |
| `soul compile [--prefix-file F] [--suffix-file F] [--reason TEXT]` | Build a new living SOUL generation if its inputs changed |
| `soul status` | Bootstrap path, active generation, history with verdicts |
| `soul rollback N` | Point `current.md` at generation N |
| `soul link HERMES_HOME` | Make `HERMES_HOME/SOUL.md` a symlink to the living SOUL |

Decision syntax: each token is `<edit-id>=accepted` or
`<edit-id>=rejected[:reason]`, reasons `too-narrow`, `too-broad`,
`already-covered`, `not-evidenced`, `unsafe`, `other`. `--decisions` can be
repeated and must be paired with `--proposal <id>`; every edit needs a
decision.
