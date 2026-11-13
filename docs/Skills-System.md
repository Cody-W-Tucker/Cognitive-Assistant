# Skills System

Skills are small, lazily loaded operating procedures an agent picks up when a
situation matches. All of them live in one store:

```text
workspaces/skills/<group>/<slug>/SKILL.md
```

`<group>` is either a profile name (generated skills) or a purpose category
for imported ones (`core`, `workflow`, `operator`, `communication`,
`domain`). Slugs are lowercase-hyphenated and unique across groups (a test
enforces this). The store is the only place consumers should read skills from:
the alignment spec, `enhance-skill` and the flake's `lib.artifacts.skills.*`
all read it. Store helpers are in `core/skill_engine.py`.

## SKILL.md contract

```yaml
---
name: scope-framing            # must equal the directory name
description: Use when ...      # required
category: operational
source_group: group-1          # required
source_profile: operational    # generated skills only
compatibility: opencode        # required, literally "opencode"
---
```

The document must be at least 200 characters, and its body must contain
`## When To Use` and `## Do Not Use`. Generated skills are validated before
they are written; `name`, `source_group`, `source_profile` and `compatibility`
are forced from the profile's `SkillSpec`, whatever the model returned.

## Generated skills (`build-skills`)

`python -m core --profile <p> build-skills [--bio PATH]` (`core/skills_creator.py`):

1. Split `human_profile.md` (or `--bio`) into its level-2 sections.
2. For each `SkillSpec` in the profile, take only the headings it names
   (`source_headings`). A missing heading fails the run.
3. If `workspaces/skills/<p>/<slug>/SKILL.md` does not exist, create it from
   `skills_creation_template.md`; otherwise refine the existing file against
   the scoped sections.
4. Validate and write.
5. Remove every directory under `workspaces/skills/<p>/` whose name is not a
   declared slug. Other groups are never touched.

Because of step 5, do not hand-place skills in a profile group; put them in a
purpose category instead.

## Imported skills

Place an external skill at `workspaces/skills/<category>/<slug>/SKILL.md` with
the frontmatter above, setting `source_group` to the upstream system or import
batch. The current imports came from Hermes and record that origin in
`source_group` (`hermes-existential`, `hermes-operational`). Re-run
`build-alignment-spec` after the skill set changes.

## Enhancing from Hermes (`enhance-skill`)

`python -m core enhance-skill [--skill SLUG] [--hermes-path PATH] [--apply]`
(`core/skill_enhancer.py`) looks for a Hermes copy of each store skill (under
`--hermes-path`, then `/var/lib/hermes/.hermes/skills`). When the Hermes copy
is newer and its body differs, it prints the diff. With `--apply` a model call
merges the Hermes changes into the store skill; the previous file is kept as a
timestamped backup unless the skill already has a marked generated section, in
which case only that section is replaced. Without `--skill` every store skill
is checked.
