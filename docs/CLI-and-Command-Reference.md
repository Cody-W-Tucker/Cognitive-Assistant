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
(deterministic, `minGapEvidence` floor) -> `synthesize` (candidate
experience record + staged artifact + informational diff) -> proposal.

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
