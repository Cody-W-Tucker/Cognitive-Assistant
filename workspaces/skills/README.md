Skills live here. This is the only primary skill store for generation,
alignment, flake consumers, similarity checks, and third-party imports.

Structure:

```text
workspaces/skills/<category>/<skill_name>/SKILL.md
```

Categories are one-level, purpose-based slugs. Generated skills use the skill's
`category` frontmatter when present, otherwise `source_group`, otherwise
`general`.

New generation, similarity checks, Hermes enhancement, and alignment generation
target this store. `workspaces/skills/<category>/<skill_name>/SKILL.md` is the
single skill workflow; profile artifact directories are not skill outputs.

## Required frontmatter

Every `SKILL.md` should carry minimal metadata so inventory and downstream
consumers can route it:

```yaml
---
name: skill-name
description: One sentence describing when the skill is useful.
category: workflow
source_group: source-or-profile-name
compatibility: opencode
---
```

Use lowercase hyphenated slugs for skill directory names. Categories are
one-level purpose buckets such as `core`, `workflow`, `operator`,
`communication`, or `domain`.

## Overlap/compression pass

Run this from the repository root:

```bash
python -m core merge-skills
```

The command scans all categories, compares frontmatter/title/body tokens, and
prints deterministic likely overlap pairs. Dry-run is the default behavior.

## Third-party imports

Bring external skills into the same flow by placing them directly at:

```text
workspaces/skills/<category>/<skill-name>/SKILL.md
```

Set `source_group` to the upstream system or import batch name. After import,
run `merge-skills` to identify local overlap and regenerate the alignment spec
if the unified skill set changed.

## Bootstrap import

The current Hermes skills are bootstrapped here under one-level purpose
categories. Their `source_group` records the original Hermes source directory:

- `hermes-existential` from `/var/lib/hermes/.hermes/skills/existential`
- `hermes-operational` from `/var/lib/hermes/.hermes/skills/operational`

Imported skill content is preserved except for normalized frontmatter required
by the workspace store (`name`, `description`, `category`, `source_group`,
`compatibility: opencode`).

## Unified skill merge workflow

Use `python -m core merge-skills` to inspect likely overlap across this unified skill store. The command is dry-run by default and reports candidates from `workspaces/skills/<category>/<skill>/SKILL.md` above `--min-score`.

The default threshold is `0.30`. Raise it when you want fewer, stronger candidates.

Use `python -m core merge-skills --apply` only when the reported candidates are safe to compress. Apply mode merges non-overlapping pairs through the shared LLM client flow used by the rest of the repo, writes the merged result to the deterministic target skill, and deletes the superseded skill directory.
