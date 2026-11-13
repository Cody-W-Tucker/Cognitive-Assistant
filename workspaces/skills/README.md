Skills live here. This is the only primary skill store for generation, alignment, flake consumers, and third-party imports.

Structure:

```text
workspaces/skills/<category>/<skill_name>/SKILL.md
```

Groups are one level deep. `build-skills` writes generated skills to `workspaces/skills/<profile>/<skill_name>/SKILL.md` and removes any skill in that profile folder the profile no longer declares, so hand-placed or imported skills belong in a purpose category (`core`, `workflow`, `operator`, `communication`, `domain`), never in a profile folder. Slugs must be unique across groups.

Skill Enhancer and alignment generation read this store; profile artifact directories are not skill outputs. See `docs/Skills-System.md`.

## Required frontmatter

Every `SKILL.md` should carry minimal metadata so downstream consumers can route it:

```yaml
---
name: skill-name
description: One sentence describing when the skill is useful.
category: workflow
source_group: source-or-category-name
compatibility: opencode
---
```

`name` must equal the directory name and `compatibility` must be `opencode`; generated skills also carry `source_profile`. The body needs `## When To Use` and `## Do Not Use` sections.

Use lowercase hyphenated slugs for skill directory names. Categories are one-level purpose buckets such as `core`, `workflow`, `operator`, `communication`, or `domain`.

## Third-party imports

Bring external skills into the same flow by placing them directly at:

```text
workspaces/skills/<category>/<skill-name>/SKILL.md
```

Set `source_group` to the upstream system or import batch name. After import,
regenerate the alignment spec if the unified skill set changed.

## Bootstrap import

The current Hermes skills are bootstrapped here under one-level purpose categories. Their `source_group` records the original Hermes source directory:

- `hermes-existential` from `/var/lib/hermes/.hermes/skills/existential`
- `hermes-operational` from `/var/lib/hermes/.hermes/skills/operational`

Imported skill content is preserved except for normalized frontmatter required by the workspace store (`name`, `description`, `category`, `source_group`, `compatibility: opencode`).
