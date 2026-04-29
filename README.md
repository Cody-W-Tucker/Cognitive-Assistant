# Overview

We use two layers to build a profile to guide AI agents on your behalf.

1. Existential Layer: Asks questions to your introspective content like journals to uncover drivers and aspirations.
2. Operational Layer: Processes your public content, work output, emails, social posts to see how you carryout actions.

These layers build on one another to create datasets to inform choices and scaffold actions with existential underpinnings.

Basically, we run systems that will explain why you choose things to AI.

This internal monologue annotates dataset with reasoning traces to introspect better and explain to AI models why/how it should do something.

## Nix Flake Outputs

This flake exposes stable paths to the generated skills and system prompt so other Nix and NixOS systems can import and use them directly.

- `lib.skillsDir`
- `lib.systemPromptFile`
- `lib.skillFile name`

Example upstream usage:

```nix
{ inputs, ... }:

let
  skill = name: builtins.readFile (inputs.cognitive-assistant.lib.skillFile name);
  systemPrompt = builtins.readFile inputs.cognitive-assistant.lib.systemPromptFile;
in
{
  programs.opencode.skills.user-context-model = skill "user-context-model";
}
```

The committed source paths also remain available directly:

- `${inputs.cognitive-assistant}/Existential-Layer/artifacts/system_prompt.md`
- `${inputs.cognitive-assistant}/Existential-Layer/artifacts/skills/<name>/SKILL.md`
