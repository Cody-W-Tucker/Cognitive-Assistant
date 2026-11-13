"""The skill store and the SKILL.md contract every skill in it follows.

Skills live at ``workspaces/skills/<group>/<slug>/SKILL.md``. Generated skills
use their profile name as the group; imported skills use a purpose category.
Slugs are unique across groups.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from core import llm, paths
from core.config import SkillSpec

MIN_SKILL_CHARS = 200
REQUIRED_SECTIONS = ("## When To Use", "## Do Not Use")


def validate_skill_slug(skill_name: str) -> None:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill_name):
        raise ValueError(f"Skill name '{skill_name}' must be a lowercase hyphenated slug")


def skill_path(group: str, slug: str) -> Path:
    validate_skill_slug(slug)
    return paths.SKILLS_DIR / group / slug / "SKILL.md"


def iter_skills() -> List[Path]:
    return sorted(paths.SKILLS_DIR.glob("*/*/SKILL.md"))


def find_skill(slug: str) -> Path | None:
    """The skill with this slug in any group."""
    validate_skill_slug(slug)
    matches = sorted(paths.SKILLS_DIR.glob(f"*/{slug}/SKILL.md"))
    return matches[0] if matches else None


def _split_frontmatter(content: str) -> tuple[str | None, str]:
    if not content.startswith("---"):
        return None, content
    parts = content.split("---", 2)
    if len(parts) != 3:
        return None, content
    return parts[1], parts[2]


def extract_frontmatter_value(content: str, key: str) -> str | None:
    """A simple scalar from the YAML frontmatter."""
    frontmatter = _split_frontmatter(content)[0]
    if frontmatter is None:
        return None
    match = re.search(rf"^{re.escape(key)}:[ \t]*(?P<value>[^\n#]+?)[ \t]*$", frontmatter, flags=re.MULTILINE)
    return match.group("value").strip().strip("\"'") if match else None


def body_without_frontmatter(content: str) -> str:
    frontmatter, body = _split_frontmatter(content)
    return body if frontmatter is not None else content


def validate_skill_document(skill_name: str, content: str, *, label: str = "Skill") -> None:
    """Check the SKILL.md contract shared by generated and imported skills."""
    if len(content.strip()) < MIN_SKILL_CHARS:
        raise ValueError(f"{label} {skill_name} is unexpectedly short")
    if extract_frontmatter_value(content, "name") != skill_name:
        raise ValueError(f"{label} {skill_name} is missing matching frontmatter name")
    for key in ("description", "source_group"):
        if extract_frontmatter_value(content, key) is None:
            raise ValueError(f"{label} {skill_name} is missing required {key} frontmatter")
    if extract_frontmatter_value(content, "compatibility") != "opencode":
        raise ValueError(f"{label} {skill_name} is missing opencode compatibility")
    for section in REQUIRED_SECTIONS:
        if section not in content:
            raise ValueError(f"{label} {skill_name} is missing '{section}' section")


def validate_declared_skill_document(spec: SkillSpec, content: str, source_profile: str) -> None:
    validate_skill_document(spec.slug, content)
    for key, expected in (("source_group", spec.source_group), ("source_profile", source_profile)):
        actual = extract_frontmatter_value(content, key)
        if actual != expected:
            raise ValueError(f"Skill {spec.slug} has {key} '{actual}', expected '{expected}'")


def with_generation_metadata(spec: SkillSpec, content: str, source_profile: str) -> str:
    """Force generated-skill identity metadata into frontmatter."""
    replacements = {
        "name": spec.slug,
        "source_group": spec.source_group,
        "source_profile": source_profile,
        "compatibility": "opencode",
    }
    updated = content.strip()
    frontmatter, body = _split_frontmatter(updated)
    replacement_lines = [f"{key}: {value}" for key, value in replacements.items()]
    if frontmatter is None:
        return f"---\n{chr(10).join(replacement_lines)}\n---\n\n{updated}"
    lines = frontmatter.strip().splitlines()
    present: set[str] = set()
    for index, line in enumerate(lines):
        for key, value in replacements.items():
            if re.match(rf"^{re.escape(key)}:\s*", line):
                lines[index] = f"{key}: {value}"
                present.add(key)
                break
    lines.extend(f"{key}: {value}" for key, value in replacements.items() if key not in present)
    body_separator = body if body.startswith("\n") else f"\n{body}"
    return f"---\n{chr(10).join(lines)}\n---{body_separator}"


async def create_declared_skill_document(
    *, spec: SkillSpec, source_profile: str, skills_creation_template: str, scoped_bio_content: str
) -> str:
    """Create one declared skill from scoped profile content."""
    base_prompt = skills_creation_template.format(grouped_bio_content=scoped_bio_content)
    prompt = f"""{base_prompt}

<declared_skill_contract>
Generate exactly one skill for this declared profile skill spec.

The JSON object must contain exactly one key: {spec.slug}

The SKILL.md frontmatter must include:
- name: {spec.slug}
- source_group: {spec.source_group}
- source_profile: {source_profile}
- compatibility: opencode

Do not invent additional skills. Do not use any profile context outside the provided skill group.
</declared_skill_contract>"""
    payload = llm.parse_json_object(await llm.complete(prompt), label="skills")
    if set(payload) != {spec.slug}:
        actual = ", ".join(sorted(payload)) or "(empty)"
        raise ValueError(f"Generated skill keys {actual}; expected exactly {{{spec.slug}}}")
    return payload[spec.slug]


async def refine_declared_skill_document(
    *, spec: SkillSpec, source_profile: str, scoped_bio_content: str, local_content: str
) -> str:
    """Refine one declared skill, seeded by its current SKILL.md."""
    prompt = f"""<task>
You are refining one existing OpenCode-compatible canonical skill from newly scoped profile context.

Use the existing canonical skill as the seed. Preserve useful local/user-authored material unless it conflicts with the scoped source context or the declared skill contract. Do not blindly recreate the skill from scratch.

<declared_skill>
slug: {spec.slug}
source_profile: {source_profile}
source_group: {spec.source_group}
</declared_skill>

<scoped_profile_context>
{scoped_bio_content.strip()}
</scoped_profile_context>

<existing_canonical_skill>
{local_content.strip()}
</existing_canonical_skill>

Write the final full markdown content for workspaces/skills/{source_profile}/{spec.slug}/SKILL.md.

Requirements:
- Return markdown only, no code fence.
- Preserve valid YAML frontmatter.
- Frontmatter must include name: {spec.slug}, description:, source_group: {spec.source_group}, source_profile: {source_profile}, category:, and compatibility: opencode.
- Keep the skill narrow and conditional.
- Include ## When To Use and ## Do Not Use sections.
- Use only the scoped profile context above for profile-derived changes.
</task>"""
    return await llm.complete(prompt, label=f"skill {spec.slug}")


async def generate_hermes_enhancement(
    *, skill_name: str, hermes_content: str, local_content: str, diff: str, context: str
) -> str:
    """Evolve one skill from its Hermes source and the local canonical copy."""
    prompt = f"""<task>
You are evolving one OpenCode-compatible skill from Hermes source material and the current canonical artifact.

Use the same capability-synthesis standard as the normal skills creation path: the skill should be conditional, operational, and useful to a downstream agent. Do not produce a scaffold, review notes, or commentary.

<skill_name>
{skill_name}
</skill_name>

<enhancement_context>
{context.strip()}
</enhancement_context>

<hermes_source_skill>
{hermes_content.strip()}
</hermes_source_skill>

<local_seed_skill>
{local_content.strip() or "(no existing canonical skill)"}
</local_seed_skill>

<hermes_to_local_diff>
{diff.strip() or "(no diff)"}
</hermes_to_local_diff>

Write the final full markdown content for workspaces/skills/<source_profile>/{skill_name}/SKILL.md.

Requirements:
- Return markdown only, no code fence.
- Preserve valid YAML frontmatter.
- Frontmatter must include name: {skill_name}, description:, source_group:, category:, and compatibility: opencode.
- Keep the skill narrow and conditional.
- Preserve high-value Hermes behavior, but adapt it to the canonical local artifact and diff.
- Preserve useful local/user-authored material unless it conflicts with the evolved skill.
- Include ## When To Use and ## Do Not Use sections.
</task>"""
    content = await llm.complete(prompt, label=f"enhanced skill {skill_name}")
    validate_skill_document(skill_name, content, label="Enhanced skill")
    return content
