# Overview

We use two layers to build a profile to guide AI agents on your behalf.

1. Existential Layer: Asks questions to your introspective content like journals to uncover drivers and aspirations.
2. Operational Layer: Processes your public content, work output, emails, social posts to see how you carryout actions.

These layers build on one another to create datasets to inform choices and scaffold actions with existential underpinnings.

Basically, we run systems that will explain why you choose things to AI.

This internal monologue annotates dataset with reasoning traces to introspect better and explain to AI models why/how it should do something.

## Nix Flake Outputs

Skills are unified under `workspaces/skills` and exposed in two downstream skill
shapes, alongside tool-spec and alignment outputs:

| Output                                               | Purpose                                                   |
| ---------------------------------------------------- | --------------------------------------------------------- |
| `lib.artifacts.skills.files.<skill-name>`            | Flat skill content keyed by skill name                    |
| `lib.artifacts.skills.names`                         | Available skill names                                     |
| `lib.artifacts.skills.categorized`                   | Categorized skill tree shaped as `<category>/<skill>/...` |
| `lib.artifacts.operational.toolSpecs.{memory,tasks}` | Operational tool specs                                    |
| `packages.<system>.verify-alignment`                 | Alignment verifier package                                |
| `lib.artifacts.alignment.spec`                       | Generated alignment spec                                  |
| `lib.artifacts.alignment.toolSpecs.verifyAlignment`  | Alignment tool spec                                       |

## Downstream Usage

```nix
{ pkgs, inputs, ... }:

let
  cognitive = inputs.cognitive-assistant;
  system = pkgs.stdenv.hostPlatform.system;
  verifyAlignment = cognitive.packages.${system}.verify-alignment;
  artifacts = cognitive.lib.artifacts;
  operational = artifacts.operational;
  alignment = artifacts.alignment;
in
{
  # Categorized Hermes-style skill tree: <category>/<skill>/SKILL.md.
  environment.etc."hermes/skills".source = artifacts.skills.categorized;

  # Operational profile tool specs.
  programs.opencode.tools = {
    memory = builtins.readFile operational.toolSpecs.memory;
    tasks = builtins.readFile operational.toolSpecs.tasks;

    # Alignment verifier tool spec.
    verifyAlignment = builtins.readFile alignment.toolSpecs.verifyAlignment;
  };

  # Alignment spec and package for verifying generated artifacts.
  environment.sessionVariables.ALIGNMENT_SPEC = "${alignment.spec}";
  environment.systemPackages = [
    verifyAlignment
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
(`existential` or `operational`) for profile-specific build steps.

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

# Cross-profile / shared commands
python -m core enhance-skill
python -m core build-alignment-spec
python -m core build-soul
```

`build-skills` reads the active profile's latest `human_profile*.md`, but writes
to the unified skill store. Cross-system consumers should read skills only from
`workspaces/skills` or `lib.artifacts.skills.*`, not from profile artifact
directories.

Generated canonical skills currently land at:

```text
workspaces/skills/<profile>/<skill-name>/SKILL.md
```

Use profile folders when the generator does not yet have a better stable
category. Do not write generated skills into opaque folders like `group-1`.

## Alignment Verification

The alignment command sits above both profiles. It reads unified skills from
`workspaces/skills` and writes a workspace artifact verification spec — a personalized
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
