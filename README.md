# Overview

We use two layers to build a profile to guide AI agents on your behalf.

1. Existential Layer: Asks questions to your introspective content like journals to uncover drivers and aspirations.
2. Operational Layer: Processes your public content, work output, emails, social posts to see how you carryout actions.

These layers build on one another to create datasets to inform choices and scaffold actions with existential underpinnings.

Basically, we run systems that will explain why you choose things to AI.

This internal monologue annotates dataset with reasoning traces to introspect better and explain to AI models why/how it should do something.

## Nix Flake Outputs

Each profile exposes its generated base context artifact, the list of skills
currently in the workspace, and a helper to read a specific skill file. The
operational profile additionally exports per-tool specs.

| Output | Existential | Operational | Alignment |
|---|---|---|---|
| `lib.<profile>.contextFile` | yes | yes | — |
| `lib.<profile>.skillsDir` | yes | yes | — |
| `lib.<profile>.skillNames` | yes | yes | — |
| `lib.<profile>.skillFile <name>` | yes | yes | — |
| `lib.<profile>.toolSpecs.{memory,tasks}` | — | yes | — |
| `packages.verify-alignment` | — | — | yes |
| `lib.alignment.spec` | — | — | yes |
| `lib.alignment.toolSpecs.verifyAlignment` | — | — | yes |
| `lib.alignment.seed` | — | — | yes |

Skill names are dynamic — read them from `skillNames` rather than hardcoding.

## Downstream Usage

Treat the exported base context artifact as the base layer and the generated
skills as conditional overlays. For both profiles, `contextFile` points to
`human_profile.md`. Then map `skillNames` to skill contents:

```nix
{ inputs, ... }:

let
  layer = inputs.cognitive-assistant.lib.existential;  # or .operational
  readSkill = name: builtins.readFile (layer.skillFile name);
in
{
  programs.opencode.context = builtins.readFile layer.contextFile;
  programs.opencode.skills = builtins.listToAttrs (
    map (name: { inherit name; value = readSkill name; }) layer.skillNames
  );
}
```

To expose only a subset of skills, filter `skillNames` before mapping:

```nix
let
  layer = inputs.cognitive-assistant.lib.operational;
  wanted = builtins.filter
    (name: builtins.elem name [ "artifact-proof-bounds" "sequence-integrity-router" ])
    layer.skillNames;
in
  builtins.listToAttrs (
    map (name: { inherit name; value = builtins.readFile (layer.skillFile name); }) wanted
  )
```

The operational profile also exports tool specs:

```nix
let
  operational = inputs.cognitive-assistant.lib.operational;
in
{
  programs.opencode.tools = {
    memory = builtins.readFile operational.toolSpecs.memory;
    tasks = builtins.readFile operational.toolSpecs.tasks;
  };
}
```

The alignment layer exports the `verify-alignment` tool spec:

```nix
let
  alignment = inputs.cognitive-assistant.lib.alignment;
in
{
  programs.opencode.tools.verifyAlignment = builtins.readFile alignment.toolSpecs.verifyAlignment;
}
```

Install the `verify-alignment` package for artifact verification:

```nix
{ pkgs, inputs, ... }:
{
  environment.systemPackages = [
    inputs.cognitive-assistant.packages.${pkgs.stdenv.hostPlatform.system}.verify-alignment
  ];
}
```

Then use it to verify any artifact against the alignment spec:

```bash
verify-alignment --file draft.md
verify-alignment --stdin < output.md
```

## Regeneration Workflow

The repo runs as one unified pipeline parameterized by a layer profile
(`existential` or `operational`). All commands take `--profile <name>`.

```bash
# Existential profile
python -m core --profile existential ingest-substrate --graph /path/to/graph.json
python -m core --profile existential ask-questions
python -m core --profile existential build-prompts
python -m core --profile existential build-skills

# Operational profile
python -m core --profile operational ingest-corpus
python -m core --profile operational ask-questions
python -m core --profile operational build-prompts
python -m core --profile operational build-skills
python -m core --profile operational build-tool-specs
```

If you need to read a generated artifact directly without going through the
flake outputs, the committed paths are:

```
workspaces/existential/artifacts/human_profile.md
workspaces/operational/artifacts/human_profile.md
workspaces/<profile>/artifacts/skills/<name>/SKILL.md
workspaces/operational/artifacts/tool_specs/<name>.md
workspaces/alignment/artifacts/alignment_spec.md
```

## Alignment Verification

The alignment command sits above both profiles. It reads skills from both
layers and writes a workspace artifact verification spec — a personalized
production-readiness checklist that a downstream verifier (`rlm`) uses to
score AI-generated artifacts.

```bash
# Build the spec (requires build-skills to have been run for at least one profile)
python -m core build-alignment-spec

# Verify an artifact against the spec
scripts/verify_alignment.sh --file path/to/artifact.md
scripts/verify_alignment.sh --stdin < artifact.md
```

The verifier returns `VERDICT: SHIP | TIGHTEN | REWORK` with per-item scores
and corrections. Regenerate the spec whenever skills change. See
[`profiles/alignment/README.md`](profiles/alignment/README.md) for architecture
and details.
