"""Shared mechanics for canonical OpenCode skill artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict

from core.config import SkillSpec
from lib.llm import LLMHandle, generate_text_async


def repo_root() -> Path:
    """Return the repository root for canonical workspace paths."""
    return Path(__file__).resolve().parents[1]


def canonical_skills_root() -> Path:
    """Return the unified canonical skills store."""
    return repo_root() / "workspaces" / "skills"


def validate_skill_slug(skill_name: str) -> None:
    """Validate a skill slug used as a directory name."""
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill_name):
        raise ValueError(f"Skill name '{skill_name}' must be a lowercase hyphenated slug")


def normalize_skill_category(category: str | None) -> str:
    """Normalize a one-level purpose category for the canonical skill store."""
    if category is None:
        return "general"
    normalized = re.sub(r"[^a-z0-9]+", "-", category.strip().lower()).strip("-")
    return normalized or "general"


def normalize_skill_profile(source_profile: str) -> str:
    """Normalize the one-level profile directory for generated skills."""
    normalized = re.sub(r"[^a-z0-9]+", "-", source_profile.strip().lower()).strip("-")
    if not normalized:
        raise ValueError("Generated skills require a source profile")
    return normalized


def extract_frontmatter_value(content: str, key: str) -> str | None:
    """Extract a simple scalar value from YAML frontmatter."""
    frontmatter = _split_frontmatter(content)[0]
    if frontmatter is None:
        return None
    match = re.search(
        rf"^{re.escape(key)}:\s*(?P<value>[^\n#]+?)\s*$",
        frontmatter,
        flags=re.MULTILINE,
    )
    if match is None:
        return None
    return match.group("value").strip().strip('"\'')


def extract_frontmatter(content: str) -> str:
    """Return a complete YAML frontmatter block, if present."""
    frontmatter = _split_frontmatter(content)[0]
    if frontmatter is None:
        return ""
    return "---" + frontmatter + "---"


def body_without_frontmatter(content: str) -> str:
    """Return markdown body content with leading YAML frontmatter removed."""
    frontmatter, body = _split_frontmatter(content)
    return body if frontmatter is not None else content


def _split_frontmatter(content: str) -> tuple[str | None, str]:
    """Split leading YAML frontmatter from markdown body using existing delimiters."""
    if not content.startswith("---"):
        return None, content
    parts = content.split("---", 2)
    if len(parts) != 3:
        return None, content
    return parts[1], parts[2]


def skill_category_from_content(content: str) -> str:
    """Derive the canonical category from minimal skill metadata."""
    return normalize_skill_category(
        extract_frontmatter_value(content, "category")
        or extract_frontmatter_value(content, "source_group")
    )


def canonical_skill_path(skill_name: str, source_profile: str) -> Path:
    """Return the canonical SKILL.md path for a skill/profile pair."""
    validate_skill_slug(skill_name)
    return canonical_skills_root() / normalize_skill_profile(source_profile) / skill_name / "SKILL.md"


def find_canonical_skill(skill_name: str, source_profile: str | None = None) -> Path | None:
    """Find a canonical skill by name, preferring the active profile layout."""
    validate_skill_slug(skill_name)
    root = canonical_skills_root()
    if source_profile is not None:
        profile_path = canonical_skill_path(skill_name, source_profile)
        if profile_path.exists():
            return profile_path
    if not root.exists():
        return None
    matches = sorted(root.glob(f"*/{skill_name}/SKILL.md"))
    return matches[0] if matches else None


def parse_json_response(response: str) -> Dict[str, str]:
    """Parse a JSON object response, optionally wrapped in a code fence."""
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", response)
    json_text = match.group(1) if match else response.strip()
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse skills JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Skills payload must be a JSON object")
    return {str(key): str(value) for key, value in parsed.items()}


def strip_markdown_fence(content: str) -> str:
    """Strip a single wrapping markdown/code fence from generated content."""
    stripped = content.strip()
    match = re.fullmatch(r"```(?:markdown|md)?\s*([\s\S]*?)\s*```", stripped)
    if match is not None:
        return match.group(1).strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        return stripped.removeprefix("```").removesuffix("```").strip()
    return stripped


def parse_markdown_response(response: str) -> str:
    """Parse a markdown response, optionally wrapped in a markdown fence."""
    match = re.search(r"```(?:markdown|md)?\s*([\s\S]*?)\s*```", response.strip())
    content = match.group(1) if match else response.strip()
    return content.strip()


def validate_skill_document(
    skill_name: str,
    content: str,
    *,
    label: str = "Skill",
) -> None:
    """Validate common OpenCode SKILL.md requirements."""
    if len(content.strip()) < 200:
        raise ValueError(f"{label} {skill_name} is unexpectedly short")
    if extract_frontmatter_value(content, "name") != skill_name:
        raise ValueError(f"{label} {skill_name} is missing matching frontmatter name")
    if extract_frontmatter_value(content, "description") is None:
        raise ValueError(f"{label} {skill_name} is missing required description frontmatter")
    if extract_frontmatter_value(content, "source_group") is None:
        raise ValueError(f"{label} {skill_name} is missing required source_group frontmatter")
    if extract_frontmatter_value(content, "compatibility") != "opencode":
        raise ValueError(f"{label} {skill_name} is missing opencode compatibility")
    if "## When To Use" not in content:
        raise ValueError(f"{label} {skill_name} is missing '## When To Use' section")
    if "## Do Not Use" not in content:
        raise ValueError(f"{label} {skill_name} is missing '## Do Not Use' section")


def validate_declared_skill_document(
    spec: SkillSpec,
    content: str,
    source_profile: str,
) -> None:
    """Validate a declared generated skill against its shared SKILL.md contract."""
    validate_skill_document(spec.slug, content)
    source_group = extract_frontmatter_value(content, "source_group")
    if source_group != spec.source_group:
        raise ValueError(
            f"Skill {spec.slug} has source_group '{source_group}', expected '{spec.source_group}'"
        )
    actual_source_profile = extract_frontmatter_value(content, "source_profile")
    if actual_source_profile != source_profile:
        raise ValueError(
            f"Skill {spec.slug} has source_profile '{actual_source_profile}', expected '{source_profile}'"
        )


def normalize_skill_markdown(content: str, fallback_frontmatter_source: str) -> str:
    """Normalize generated markdown and restore frontmatter when needed."""
    normalized = strip_markdown_fence(content).strip()
    if not normalized:
        raise ValueError("LLM returned an empty skill")
    if normalized.startswith("---"):
        return normalized + "\n"
    frontmatter = extract_frontmatter(fallback_frontmatter_source)
    if frontmatter:
        return frontmatter.rstrip() + "\n" + normalized + "\n"
    return normalized + "\n"


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
    present_keys: set[str] = set()
    for index, line in enumerate(lines):
        for key, value in replacements.items():
            if re.match(rf"^{re.escape(key)}:\s*", line):
                lines[index] = f"{key}: {value}"
                present_keys.add(key)
                break
    for key, value in replacements.items():
        if key not in present_keys:
            lines.append(f"{key}: {value}")

    body_separator = body if body.startswith("\n") else f"\n{body}"
    return f"---\n{chr(10).join(lines)}\n---{body_separator}"


async def create_declared_skill_document(
    *,
    handle: LLMHandle,
    spec: SkillSpec,
    source_profile: str,
    skills_creation_template: str,
    scoped_bio_content: str,
    temperature: float,
    max_output_tokens: int,
) -> str:
    """Create one declared skill document from scoped profile content."""
    prompt = build_declared_skill_creation_prompt(
        spec=spec,
        source_profile=source_profile,
        skills_creation_template=skills_creation_template,
        scoped_bio_content=scoped_bio_content,
    )
    response = await generate_text_async(
        handle,
        user_prompt=prompt,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
    payload = parse_json_response(response)
    if set(payload) != {spec.slug}:
        expected = "{" + spec.slug + "}"
        actual = ", ".join(sorted(payload)) or "(empty)"
        raise ValueError(f"Generated skill keys {actual}; expected exactly {expected}")
    return payload[spec.slug]


async def refine_declared_skill_document(
    *,
    handle: LLMHandle,
    spec: SkillSpec,
    source_profile: str,
    scoped_bio_content: str,
    local_content: str,
    temperature: float,
    max_output_tokens: int,
) -> str:
    """Refine one declared skill document from a canonical local seed."""
    prompt = build_declared_skill_refinement_prompt(
        spec=spec,
        source_profile=source_profile,
        scoped_bio_content=scoped_bio_content,
        local_content=local_content,
    )
    response = await generate_text_async(
        handle,
        user_prompt=prompt,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
    return parse_markdown_response(response)


async def generate_hermes_enhancement(
    *,
    handle: LLMHandle,
    skill_name: str,
    hermes_content: str,
    local_content: str,
    diff: str,
    context: str,
    temperature: float,
    max_output_tokens: int,
) -> str:
    """Generate one enhanced SKILL.md from source material and local seed context."""
    prompt = build_hermes_enhancement_prompt(
        skill_name=skill_name,
        hermes_content=hermes_content,
        local_content=local_content,
        diff=diff,
        context=context,
    )
    response = await generate_text_async(
        handle,
        user_prompt=prompt,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
    content = parse_markdown_response(response)
    validate_skill_document(skill_name, content, label="Enhanced skill")
    return content


def build_declared_skill_creation_prompt(
    *,
    spec: SkillSpec,
    source_profile: str,
    skills_creation_template: str,
    scoped_bio_content: str,
) -> str:
    """Build the prompt for creating one declared skill."""
    base_prompt = skills_creation_template.format(grouped_bio_content=scoped_bio_content)
    return f"""{base_prompt}

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


def build_declared_skill_refinement_prompt(
    *,
    spec: SkillSpec,
    source_profile: str,
    scoped_bio_content: str,
    local_content: str,
) -> str:
    """Build the prompt for refining one declared skill."""
    return f"""<task>
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


def build_hermes_enhancement_prompt(
    *,
    skill_name: str,
    hermes_content: str,
    local_content: str,
    diff: str,
    context: str,
) -> str:
    """Build the prompt for enhancing one canonical skill from source material."""
    return f"""<task>
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
