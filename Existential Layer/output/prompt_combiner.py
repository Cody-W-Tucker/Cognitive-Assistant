#!/usr/bin/env python3
"""
Template-Based Prompt Combiner

The script automatically loads all .md files from the prompt_parts/ directory
and makes them available as variables in your template.

Usage:
    python prompt_combiner.py  # Creates prompt.md in the same directory

Variables available:
File paths become variables: tools_memory is {folder}_{filename}
"""

import sys
import textwrap
from pathlib import Path


def load_prompts(prompts_dir):
    """Load all prompt files into a dictionary."""
    prompts = {}

    # Find all .md files recursively
    for md_file in Path(prompts_dir).rglob("*.md"):
        # Create variable name from path
        rel_path = md_file.relative_to(prompts_dir)
        var_name = str(rel_path).replace('.md', '').replace('/', '_').replace('-', '_')

        # Read file content
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                prompts[var_name] = f.read().strip()
        except Exception as e:
            print(f"Error reading {md_file}: {e}", file=sys.stderr)
            prompts[var_name] = ""

    return prompts


def main():
    # Load all prompts from Prompts directory
    prompts_dir = Path(__file__).parent / "prompt_parts"
    prompts = load_prompts(prompts_dir)

    # Add prompt structure with the template to introduce the different sections
    # Keep the formatting of the template simple, things will carry over to the final prompt and I don't want to write formatting code.
    template = '''You are the Cognitive Assistant...

{assistant_main}

You have access to these tools:

# Tool Specs

{tools_sequential_protocol}

## Memory Tool
Store preferences/rules in Memory.

{tools_memory}

## Obsidian Tool
For reflections or ideas, save to Obsidian's Inbox or Projects folder.

{tools_obsidian}

## Todoist Tool
For actionable tasks, save to Todoist with a clear title, owner, and due date (Priority 1–4 based on urgency).

{tools_todoist}'''

    # Clean up formatting and fill template with prompt content
    template = textwrap.dedent(template).strip()
    final_prompt = template.format(**prompts)

    # Write to prompt.md file
    output_file = Path(__file__).parent / "prompt.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_prompt)

    print(f"Combined prompt saved to: {output_file}")


if __name__ == "__main__":
    main()
