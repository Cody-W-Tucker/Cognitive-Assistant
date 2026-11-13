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
