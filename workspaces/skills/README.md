Skills live here. This is the only primary skill store for generation, alignment, flake consumers, and third-party imports.

Structure:

```text
workspaces/skills/<category>/<skill_name>/SKILL.md
```

Categories are one-level, purpose-based slugs. Generated skills use the skill's `category` frontmatter when present, otherwise `source_group`, otherwise `general`.

New skills, Skill Enhancer, and alignment generation target this store. `workspaces/skills/<category>/<skill_name>/SKILL.md` is the generated skill workflow; profile artifact directories are not skill outputs.

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
