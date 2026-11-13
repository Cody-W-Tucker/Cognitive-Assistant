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

A new generation is written only when the output changes. `improve-apply`
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

1. Analyze new Hermes sessions. Each evidence record carries `sessionAt`, and
   `soul/activations.jsonl` maps that time to the generation that was live.
2. Judge the active generation against the one it replaced. A session is a
   *miss* when the analysis found a quote-backed harm or non-compliance
   negative, or a gap. The verdict is `pending` until both generations have
   `--min-sessions` analyzed Hermes sessions (default 15), then `revert` if the
   miss rate rose with a one-sided two-proportion z above 1.645, else `keep`.
   Verdicts are final and recorded in `soul/verdicts.jsonl` and the journal.
3. `revert` withdraws the records that generation added (`reverted.jsonl`, kept
   as lineage), logs them in `improve/rejections.jsonl` with reason
   `reverted` so later runs do not propose them again on the same sessions,
   and compiles without them. `pending` adopts nothing. `keep` adopts the
   first record the annotation stage kept (never one withdrawn before), as a
   new generation,
   but only once the active generation has `--min-sessions` sessions of its
   own, since those are the baseline the new change will be judged against.
   On a fresh install the first weeks only build that baseline.

So exactly one change is under test at a time, and every change is judged by
what happened in sessions after it, scored by the same analysis prompt and
model as the sessions before it. A generation from a new bootstrap is kept
untested; rebootstrapping is the person's decision.

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
weekly user timer with `HERMES_HOME` and the `CA_LLM_*` endpoint variables set.
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
