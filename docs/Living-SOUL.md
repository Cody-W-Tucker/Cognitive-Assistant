# Living SOUL

The repo is the bootstrap: it collects source data and builds the bootstrap
SOUL (`workspaces/alignment/artifacts/SOUL.md`). What Hermes runs is the
*living* SOUL, which lives under CA home. Only a deliberate rebootstrap
brings runtime lineage back into the repo (see [Alignment Artifacts](Alignment-Artifacts.md)).
Code: `core/living_soul.py` (generations), `core/experience.py` (records),
`core/outcome.py` (verdicts), `core/improve.py` (`auto_cycle`).

```
<CA home>/                       $CA_HOME or $XDG_DATA_HOME/cognitive-assistant
  experience/authored/<id>.md    accepted change records (the lineage)
  experience/reverted.jsonl      records withdrawn after adoption
  improve/journal/events.jsonl   ordered history of runs, accepts, compiles
  soul/compose.json              deployer wrapper files (prefix/suffix)
  soul/generations/NNNN.md       every compiled SOUL, never edited
  soul/generations/NNNN.json     its inputs: bootstrap sha, record ids, reason
  soul/current.md                symlink to the active generation
  soul/activations.jsonl         when each generation became active
  soul/verdicts.jsonl            outcome verdict per generation
$HERMES_HOME/SOUL.md             symlink to soul/current.md
```

## Compile

A generation is a pure function of the wrapper, the bootstrap SOUL and the
active records: `prefix + bootstrap + "## Learned in use" + suffix`. It never
reads the previous generation, so changes cannot compound on their own output.
Active records are accepted records minus reverted ones minus those listed in
`absorbed.json` beside the bootstrap SOUL. Only each record's instruction goes
into the SOUL; its evidence stays in the lineage.

A generation is its text. A new one is written only for text that no earlier
generation holds; compiling text an earlier generation already holds
reactivates that generation, so after a revert the sessions it already ran
remain the baseline for the next change. `improve-apply`
compiles after accepting records; Home Manager activation compiles after a
rebuild (a new bootstrap) and links Hermes to it.

```bash
ca soul compile [--prefix-file F --suffix-file F] [--reason TEXT]
ca soul status
ca soul rollback <generation>
ca soul link <hermes-home>
```

## Outcome check and autonomous changes

`improve-run --headless --auto` (what the Home Manager timer runs) makes one
step per run:

1. Analyze new Hermes sessions and score the outcome of sessions that have
   matured (see [Improvement Loop](Improvement-Loop.md#delayed-outcome-scoring)).
   `soul/activations.jsonl` maps each evidence record's `sessionAt`, the
   session start, to the generation that was live.
2. Judge the active generation against the one it replaced. A session is a
   *miss* when its outcome label is `stalled` or `regressed`, and not a miss
   when it is `advanced`. Sessions labelled `unclear`, and sessions with no
   outcome yet, count on neither side. The analysis findings (harm,
   non-compliance, gaps) feed proposals and play no part in the verdict. The
   verdict is `pending` until both generations have `--min-sessions` scored
   Hermes sessions (default 15), then `revert` if the miss rate rose with a
   one-sided two-proportion z above `--z-threshold` (default 1.645), else
   `keep`. A `keep` row also records `improved: true` when the miss rate fell
   by the same margin; that is reporting only. Only sources `desktop`, `tui`
   and `cli` count; other or missing sources can still produce gaps but do not
   count toward a verdict. Verdicts are final and recorded in
   `soul/verdicts.jsonl` and the journal.
3. `revert` withdraws the records that generation added (`reverted.jsonl`, kept
   as lineage), logs them in `improve/rejections.jsonl` with reason
   `reverted` so later runs do not propose them again on the same sessions,
   and compiles without them. `pending` adopts nothing. `keep` adopts the
   first record the annotation stage kept (never one withdrawn before), as a
   new generation,
   but only once the active generation has `--min-sessions` sessions of its
   own, since those are the baseline the new change will be judged against.
   On a fresh install the first weeks only build that baseline.

So exactly one change is under test at a time. A comparison stays pending if
the outcomes it would count were scored under different rubrics: a different
outcome prompt hash, model or maturation window, including a mix within one
generation. An outcome without a rubric is its own rubric and cannot be mixed
with stamped ones. The analysis rubric on the evidence is recorded and not
compared; the outcome judge never sees the SOUL or the records, so both sides
are scored by the same text.

A generation that added no records (the wrapper text changed on a Home Manager
activation) does not end the test of the generation before it: their sessions
are pooled and the verdict goes to the generation that added the records.

The thresholds live in one place, `OutcomePolicy` in `core/outcome.py`:
`min_sessions`, `z_threshold`, the harness and the source allowlist. A generation from a new bootstrap is kept untested;
rebootstrapping is the person's decision.

What the metric does not control for: the mix of work changes from week to
week, and the judge is an LLM. Quote validation is limited to the analysis
output, as described in [Improvement Loop](Improvement-Loop.md#stages-of-improve-run);
`ca soul status` shows every verdict.

## Rebootstrap

Runs when you choose to: `python -m core build-translation-layer` (or
`update`) on a machine whose CA home holds the lineage. It reads source data
together with every record under `experience/authored/` (adopted and
withdrawn), writes a new bootstrap SOUL plus `absorbed.json` naming the
adopted records it took into account, and those records then drop out of the
learned section on the next compile. See
[Alignment Artifacts](Alignment-Artifacts.md).

## Home Manager

`homeManagerModules.cognitive-assistant` owns `$HERMES_HOME/SOUL.md` (remove it
from `hermesHomeFiles`, which would overwrite the link), compiles on
activation (`ca soul compile` then `ca soul link`), and runs
`ca improve-run --headless --auto --min-sessions <n> --harness hermes` from a
daily user timer with `HERMES_HOME` and the `CA_LLM_*` endpoint variables set.
Every model call is a tool-free chat completion to `llm.baseUrl` (see
[Improvement Loop](Improvement-Loop.md)); no agent harness runs. Other options:
`improve.enable`, `improve.auto`, `improve.minSessions`, `improve.harnesses`,
`improve.timerConfig`, `llm.roleModels`, `llm.apiKeyFile`, `package`.

```nix
services.cognitive-assistant = {
  enable = true;
  hermesHome = config.services.hermes-agent.hermesHome;
  soul.prefix = brevityInstructions + delegationInstructions;
  soul.suffix = agentsDocument;
  llm = {
    baseUrl = "http://127.0.0.1:8081/v1";   # llama-swap on the NAS
    model = "qwen-3.6-35b-a3b";
  };
};
```

### Outcome evidence

Outcome scoring waits three days by default and records advanced, stalled,
regressed, or unclear using a blind rubric. Unclear means the available
follow-up does not decide; an unscored session has not yet supplied a verdict.
For outcome-based verdicts, stalled and regressed are misses; advanced is not,
and unclear and unscored sessions are excluded. Outcome rubric versions must
match before comparing generations. The backtest and measured volume setting
in `plans/feature-2.md` still require human review; do not infer a calibrated
sample size from the default.
