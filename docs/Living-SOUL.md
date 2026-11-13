# Living SOUL

The repo is the bootstrap: it collects source data and builds the bootstrap
SOUL (`workspaces/alignment/artifacts/SOUL.md`). What Hermes runs is the
*living* SOUL, which lives in CA's state dir and never flows back into the repo.

```
<CA home>/                       $CA_HOME or $XDG_DATA_HOME/cognitive-assistant
  experience/authored/<id>.md    accepted change records (the lineage)
  experience/reverted.jsonl      records withdrawn after adoption
  improve/journal/events.jsonl   ordered history of runs, accepts, compiles
  soul/compose.json              deployer wrapper files (prefix/suffix)
  soul/generations/NNNN.md       every compiled SOUL, never edited
  soul/generations/NNNN.json     its inputs: bootstrap sha, record ids, reason
  soul/current.md                symlink to the active generation
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
   as lineage) and compiles without them. `pending` adopts nothing. `keep`
   adopts the first record the annotation stage kept, as a new generation,
   but only once the active generation has `--min-sessions` sessions of its
   own, since those are the baseline the new change will be judged against.
   On a fresh install the first weeks only build that baseline.

So exactly one change is under test at a time, and every change is judged by
what happened in sessions after it, scored by the same analysis prompt and
model as the sessions before it. A generation from a new bootstrap is kept
untested; rebootstrapping is the person's decision.

What the metric does not control for: the mix of work changes from week to
week, and the judge is an LLM. Quote binding keeps each miss traceable to a
verbatim line of the session, and `ca soul status` shows every verdict.

## Rebootstrap

Runs on the NAS when you choose to. It reads source data together with the
lineage under CA home, writes a new bootstrap SOUL plus `absorbed.json` naming
the records it took into account, and those records then drop out of the
learned section on the next compile.

## Home Manager

`homeManagerModules.cognitive-assistant` owns `$HERMES_HOME/SOUL.md` (remove it
from `hermesHomeFiles`, which would overwrite the link), compiles on
activation, and runs `ca-improve --headless --harness hermes` weekly with
`HERMES_HOME` set.

```nix
services.cognitive-assistant = {
  enable = true;
  hermesHome = config.services.hermes-agent.hermesHome;
  soul.prefix = brevityInstructions + delegationInstructions;
  soul.suffix = agentsDocument;
};
```
