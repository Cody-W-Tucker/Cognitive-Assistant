<task>
You are generating a small set of personalized tool specs from an operational profile.

These specs are system-prompt skeletons for single-tool agents. Each output file should tell a specialized agent how to use one tool in a way that matches this specific user.

The generic tool documents are exemplars. They describe what the tool means in the abstract. Your job is to convert the most useful ones into personalized operational guidance weighted toward the user's actual profile.

<supported_tools>
{supported_tools}
</supported_tools>

<input_profile>
{bio_content}
</input_profile>

<generic_tool_examples>
{seed_documents}
</generic_tool_examples>

<goal>
Produce personalized tool specs for the supported tool set above. Do not invent additional tools and do not omit any supported tool.

The output should not be a generic description of the tool. It should answer questions like:
- what kinds of things are especially valuable for this user to store, retrieve, capture, or format with this tool
- what should the tool agent prioritize when the user asks for help
- what generic tool behavior would be noisy, over-eager, or off-target for this user
- what defaults would make the tool useful without repeated supervision
</goal>

<selection_rules>
1. Emit exactly one file for each supported tool listed above.
2. Do not invent additional tool categories.
3. Preserve the idea of the generic tool, but rewrite it so the center of gravity is this user's actual preferences and working style.
4. If the profile gives weak evidence for a tool, still produce the file, but keep it conservative and clearly bounded.
</selection_rules>

<output_requirements>
Each file is a system-prompt skeleton for a one-tool agent.

Each file must include:
- a title line
- `## Mission`
- `## Use This Tool For`
- `## Decision Rules`
- `## Avoid`

Add other sections only when they improve execution, such as:
- `## What To Store`
- `## Retrieval Priorities`
- `## Task Shaping`
- `## Writing Style`
- `## Workflow`
- `## Examples`

The content should:
- read like instructions to a tool-managing agent
- stay concrete and operational
- make the user's likely preferences visible
- make high-value default behavior obvious
- distinguish what matters most for this user from generic tool usage
- avoid sounding like a marketing blurb or generic best-practices article
</output_requirements>

<tool_specific_guidance>
- For memory: emphasize the types of facts, preferences, decisions, and continuity cues most worth storing for this user; also say what not to clutter memory with.
- For memory: preserve the distinction between insert, update, delete, and no-op; specify what kinds of memories are worth each action for this user; and call out whether temporal context, activity details, entity nuances, or relationships are especially worth capturing.
- For task tools: emphasize how to identify real commitments, how much decomposition is helpful, and what kinds of captures would become overhead.
</tool_specific_guidance>

<output_format>
Return a JSON object and nothing else.

Each key must be one of the supported markdown filenames listed above.
Each value must be the full markdown contents of that file.

Example shape:
{{
  "memory.md": "# Memory Agent\n\n## Mission\n...",
  "tasks.md": "# Task Agent\n\n## Mission\n..."
}}
</output_format>

<quality_bar>
Before producing the final JSON, verify:
1. Each file could plausibly be used as the system prompt for a one-tool agent.
2. The center of gravity is the user profile, not the generic example.
3. The specs make tool use more selective and useful, not broader.
4. The result tells the agent what matters most for this user.
5. The output covers the supported set exactly and nothing else.
</quality_bar>
</task>
