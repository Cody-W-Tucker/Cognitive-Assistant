# Overview

We use two layers to build a profile to guide AI agents on your behalf.

1. Existential Layer: Asks questions to your introspective content like journals to uncover drivers and aspirations.
2. Operational Layer: Processes your public content, work output, emails, social posts to see how you carryout actions.

These layers build on one another to create datasets to inform choices and scaffold actions with existential underpinnings.

Basically, we run systems that will explain why you choose things to AI.

This internal monologue annotates dataset with reasoning traces to introspect better and explain to AI models why/how it should do something.

## Nix Flake Outputs

Skills are unified under `workspaces/skills` and exposed in two downstream skill
shapes, alongside translation-layer and alignment outputs:

| Output                                               | Purpose                                                   |
| ---------------------------------------------------- | --------------------------------------------------------- |
| `lib.artifacts.skills.files.<skill-name>`            | Flat skill content keyed by skill name                    |
| `lib.artifacts.skills.names`                         | Available skill names                                     |
| `lib.artifacts.skills.categorized`                   | Categorized skill tree shaped as `<category>/<skill>/...` |
| `lib.artifacts.alignment.spec`                       | Generated alignment spec                                  |
| `lib.artifacts.alignment.translationLayer`           | Generated translation-layer orchestrator soul (SOUL.md)   |
| `lib.artifacts.alignment.interactionPosture`       | Generated interaction posture (INTERACTION_POSTURE.md) |
| `lib.artifacts.operational.toolSpecs.{memory,tasks}` | Operational tool specs                                    |

## Downstream Usage

```nix
{ pkgs, inputs, ... }:

let
  cognitive = inputs.cognitive-assistant;
  system = pkgs.stdenv.hostPlatform.system;
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

  };

  # Generated alignment spec.
  environment.sessionVariables.ALIGNMENT_SPEC = "${alignment.spec}";
}
```

## Regeneration Workflow

The repo runs as one unified pipeline parameterized by a layer profile
(`existential` or `operational`) for profile-specific build steps.

```bash
# Existential profile
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
python -m core build-translation-layer
python -m core build-alignment-spec
```

Question answering retrieves from configured QMD collections. Existential uses
`Journal` and `Personal`; operational uses `Base`, `Consulting`, and `Customers`.
Raw source notes are not copied into this repository.

`build-skills` reads the active profile's latest `human_profile*.md`, but writes
to the unified skill store. Cross-system consumers should read skills only from
`workspaces/skills` or `lib.artifacts.skills.*`, not from profile artifact
directories.

Generated canonical skills land at:
`workspaces/skills/<profile>/<skill-name>/SKILL.md`

`build-translation-layer` reads both profile artifacts and produces the
orchestrator translation layer: the interaction posture inference and the
durable orchestrator soul. Outputs land at:
`workspaces/alignment/artifacts/INTERACTION_POSTURE.md`
`workspaces/alignment/artifacts/SOUL.md`

```text
workspaces/skills/<profile>/<skill-name>/SKILL.md
workspaces/alignment/artifacts/INTERACTION_POSTURE.md
workspaces/alignment/artifacts/SOUL.md
```

Use profile folders when the generator does not yet have a better stable
category. Do not write generated skills into opaque folders like `group-1`.

## Alignment Spec

The alignment command sits above both profiles. It reads unified skills from
`workspaces/skills` and writes a personalized production-readiness checklist.

```bash
# Build the spec (requires build-skills to have been run)
python -m core build-alignment-spec

```

Regenerate the spec whenever skills change. See
[`profiles/alignment/README.md`](profiles/alignment/README.md) for architecture
and details.
