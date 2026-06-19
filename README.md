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

| Output                                     | Purpose                                                    |
| ------------------------------------------ | ---------------------------------------------------------- |
| `packages.<system>.skills`                 | Flat export shaped as `<skill>/SKILL.md`                   |
| `packages.<system>.categorizedSkills`      | Categorized export shaped as `<category>/<skill>/SKILL.md` |
| `lib.operational.toolSpecs.{memory,tasks}` | Operational tool specs                                     |
| `packages.<system>.verify-alignment`       | Alignment verifier package                                 |
| `lib.alignment.spec`                       | Generated alignment spec                                   |
| `lib.alignment.toolSpecs.verifyAlignment`  | Alignment tool spec                                        |

## Downstream Usage

```nix
{ pkgs, inputs, ... }:

let
  cognitive = inputs.cognitive-assistant;
  system = pkgs.stdenv.hostPlatform.system;
  flatSkills = cognitive.packages.${system}.skills;
  categorizedSkills = cognitive.packages.${system}.categorizedSkills;
  verifyAlignment = cognitive.packages.${system}.verify-alignment;
  operational = cognitive.lib.operational;
  alignment = cognitive.lib.alignment;
in
{
  # Flat OpenCode-style skill tree: <skill>/SKILL.md.
  # Requires globally unique skill slugs across workspaces/skills/*/*.
  environment.etc."opencode/skills".source = flatSkills;

  # Categorized Hermes-style skill tree: <category>/<skill>/SKILL.md.
  environment.etc."hermes/skills".source = categorizedSkills;

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
`workspaces/skills`, `packages.<system>.skills`, or
`packages.<system>.categorizedSkills`, not from profile artifact directories.

Generated canonical skills currently land at:

```text
workspaces/skills/<profile>/<skill-name>/SKILL.md
```

Use profile folders when the generator does not yet have a better stable
category. Do not write generated skills into opaque folders like `group-1`.

### Third-party skill import

Bring external skills into the same flow by adding them directly under the
unified store:

```text
workspaces/skills/<category>/<skill-name>/SKILL.md
```

Use one-level purpose categories (`workflow`, `communication`, `core`, etc.) for
manually maintained skills and lowercase hyphenated skill slugs. Each `SKILL.md`
should include frontmatter:

```yaml
---
name: skill-name
description: One sentence describing when the skill is useful.
category: workflow
source_group: third-party-source-name
compatibility: opencode
---
```

then regenerate the alignment spec if the skill set changed.

To preview source material against the local canonical skill with Skill Enhancer, run:

```bash
python -m core enhance-skill
python -m core enhance-skill --skill skill-name
python -m core enhance-skill --apply
python -m core enhance-skill --skill skill-name --apply
```

`enhance-skill` is dry-run by default. It shows the named source material, the
canonical target skill path, and the current diff before any write. If you omit
`--skill`, it iterates over every discovered workspace skill.

If you need to read a generated artifact directly without going through the
flake outputs, the committed paths are:

```
workspaces/existential/artifacts/human_profile.md
workspaces/operational/artifacts/human_profile.md
workspaces/skills/<category-or-profile>/<name>/SKILL.md
workspaces/operational/artifacts/tool_specs/<name>.md
workspaces/alignment/artifacts/alignment_spec.md
```

For downstream skill consumers specifically, the two skill package outputs both
include all skills by default:

- `packages.<system>.skills`
  - export tree shaped as `<skill>/SKILL.md`
- `packages.<system>.categorizedSkills`
  - export tree shaped as `<category>/<skill>/SKILL.md`

`skills` strips the category directory for OpenCode-style consumers.
`categorizedSkills` preserves the category directory for Hermes-style
consumers. Flat export assumes globally unique skill names across categories;
that invariant is enforced by repo tests.

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
