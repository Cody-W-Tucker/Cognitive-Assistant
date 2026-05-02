# Overview

We use two layers to build a profile to guide AI agents on your behalf.

1. Existential Layer: Asks questions to your introspective content like journals to uncover drivers and aspirations.
2. Operational Layer: Processes your public content, work output, emails, social posts to see how you carryout actions.

These layers build on one another to create datasets to inform choices and scaffold actions with existential underpinnings.

Basically, we run systems that will explain why you choose things to AI.

This internal monologue annotates dataset with reasoning traces to introspect better and explain to AI models why/how it should do something.

## Nix Flake Outputs

This flake exposes both layers separately so downstream systems can load the generated system prompts, whatever skills currently exist for each layer, and the operational tool specs.

- `lib.existential.skillsDir`
- `lib.existential.systemPromptFile`
- `lib.existential.skillNames`
- `lib.existential.skillFile name`

- `lib.operational.skillsDir`
- `lib.operational.systemPromptFile`
- `lib.operational.skillNames`
- `lib.operational.skillFile name`
- `lib.operational.toolSpecs.memory`
- `lib.operational.toolSpecs.tasks`

## Downstream Usage

Downstream systems should treat the system prompt as the base layer and the generated skills as conditional overlays.

Suggested model:

1. Load one layer's `systemPromptFile` as background operating guidance.
2. Inspect that layer's `skillNames` to see which generated skills exist.
3. Load only the few skills and tool specs that match the current situation.

The skill names are now dynamic.
Do not hardcode assumptions like `user-context-model` or `user-workflow-sequencing` unless you are pinning to a specific commit that contains those names.
Instead, consume `skillNames` from the flake and select from the generated set.
The operational tool specs are exported explicitly as `memory` and `tasks`.

Example upstream usage:

```nix
{ inputs, ... }:

let
  existential = inputs.cognitive-assistant.lib.existential;
  skill = name: builtins.readFile (existential.skillFile name);
  systemPrompt = builtins.readFile existential.systemPromptFile;
in
{
  programs.opencode.context = systemPrompt;
  programs.opencode.skills = builtins.listToAttrs (
    map
      (name: {
        inherit name;
        value = skill name;
      })
      existential.skillNames
  );
}
```

Operational layer example:

```nix
{ inputs, ... }:

let
  operational = inputs.cognitive-assistant.lib.operational;
  skill = name: builtins.readFile (operational.skillFile name);
  systemPrompt = builtins.readFile operational.systemPromptFile;
in
{
  programs.opencode.context = systemPrompt;
  programs.opencode.skills = builtins.listToAttrs (
    map
      (name: {
        inherit name;
        value = skill name;
      })
      operational.skillNames
  );
}
```

Operational tool spec example:

```nix
{ inputs, ... }:

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

If you want to selectively expose only some skills, filter `skillNames` first.

```nix
let
  operational = inputs.cognitive-assistant.lib.operational;
  wanted = builtins.filter (name: builtins.elem name [
    "artifact-proof-bounds"
    "sequence-integrity-router"
  ]) operational.skillNames;
in
  builtins.listToAttrs (map (name: {
    inherit name;
    value = builtins.readFile (operational.skillFile name);
  }) wanted)
```

## Regeneration Workflow

The flake exports the generated artifacts that are currently committed in the repo.
If you regenerate prompts or skills, downstream consumers will see the new names and contents after that commit is updated.

Typical regeneration commands:

```bash
python Existential-Layer/prompt_creator.py
python Existential-Layer/skills_creator.py

python Operational-Layer/prompt_creator.py
python Operational-Layer/skills_creator.py
```

The committed source paths also remain available directly:

- `${inputs.cognitive-assistant}/Existential-Layer/artifacts/system_prompt.md`
- `${inputs.cognitive-assistant}/Existential-Layer/artifacts/skills/<name>/SKILL.md`
- `${inputs.cognitive-assistant}/Operational-Layer/artifacts/system_prompt.md`
- `${inputs.cognitive-assistant}/Operational-Layer/artifacts/skills/<name>/SKILL.md`
- `${inputs.cognitive-assistant}/Operational-Layer/artifacts/tool_specs/<name>.md`
