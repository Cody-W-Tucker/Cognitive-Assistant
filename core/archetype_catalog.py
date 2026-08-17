"""Strict catalog loader for the predefined agent archetypes.

The catalog intentionally uses JSON rather than a partial YAML implementation:
these are small checked-in contracts, the development environment has no YAML
parser dependency, and JSON gives malformed input deterministic failures.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from core.config import ROOT_DIR
from core.skill_engine import find_canonical_skill, validate_skill_slug


ARCHETYPES_DIR = ROOT_DIR / "profiles" / "alignment" / "archetypes"
EXPECTED_ARCHETYPE_SLUGS = frozenset(
    {
        "pattern-scout",
        "constraint-reader",
        "commitment-anchor",
    }
)
_REQUIRED_FIELDS = frozenset(
    {
        "slug",
        "name",
        "purpose",
        "job_to_be_done",
        "outcome",
        "scope",
        "authority",
        "approval_boundaries",
        "quality_expectations",
        "evidence_expectations",
        "canonical_skills",
    }
)
_SCOPE_FIELDS = frozenset({"triggers", "outputs", "out_of_scope"})
_AUTHORITY_FIELDS = frozenset({"can_decide", "must_defer"})


@dataclass(frozen=True)
class ArchetypeSpec:
    """A predefined agent archetype with a complete operating contract."""

    slug: str
    name: str
    purpose: str
    job_to_be_done: str
    outcome: str
    scope_triggers: List[str]
    scope_outputs: List[str]
    out_of_scope: List[str]
    authority_can_decide: List[str]
    authority_must_defer: List[str]
    approval_boundaries: str
    quality_expectations: str
    evidence_expectations: str
    canonical_skills: List[str]

    def contract_text(self) -> str:
        """Render the full operating contract as human-readable text."""
        sections = [
            ("Scope — triggers", self.scope_triggers),
            ("Scope — outputs", self.scope_outputs),
            ("Out of scope", self.out_of_scope),
            ("Authority — can decide", self.authority_can_decide),
            ("Authority — must defer", self.authority_must_defer),
            ("Canonical skills", self.canonical_skills),
        ]
        lines = [
            f"# {self.name} ({self.slug})",
            "",
            f"**Purpose:** {self.purpose}",
            "",
            f"**Job to be done:** {self.job_to_be_done}",
            "",
            f"**Outcome:** {self.outcome}",
            "",
        ]
        for heading, values in sections[:5]:
            lines.append(f"**{heading}:**")
            lines.extend(f"- {value}" for value in values)
            lines.append("")
        lines.extend(
            [
                f"**Approval boundaries:** {self.approval_boundaries}",
                "",
                f"**Quality expectations:** {self.quality_expectations}",
                "",
                f"**Evidence expectations:** {self.evidence_expectations}",
                "",
                f"**{sections[5][0]}:**",
            ]
        )
        lines.extend(f"- {value}" for value in sections[5][1])
        return "\n".join(lines)


def _ensure_str(value: object, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Archetype field '{key}' must be a non-empty string")
    return value.strip()


def _ensure_list(value: object, key: str) -> List[str]:
    if not isinstance(value, list):
        raise ValueError(f"Archetype field '{key}' must be a non-empty list")
    if not value:
        raise ValueError(f"Archetype field '{key}' must not be empty")
    items: List[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"Archetype field '{key}' item {index} must be a non-empty string"
            )
        items.append(item.strip())
    duplicates = sorted({item for item in items if items.count(item) > 1})
    if duplicates:
        raise ValueError(
            f"Archetype field '{key}' contains duplicate value(s): {', '.join(duplicates)}"
        )
    return items


def _ensure_mapping(value: object, key: str, expected_keys: frozenset[str]) -> Dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Archetype field '{key}' must be an object")
    actual_keys = set(value)
    missing = expected_keys - actual_keys
    extra = actual_keys - expected_keys
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing: {', '.join(sorted(missing))}")
        if extra:
            details.append(f"unknown: {', '.join(sorted(extra))}")
        raise ValueError(f"Archetype field '{key}' has invalid keys ({'; '.join(details)})")
    return value


def _parse_archetype_file(path: Path) -> ArchetypeSpec:
    """Parse and validate one JSON contract file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Archetype file {path.name} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Archetype file {path.name} must contain a JSON object")

    actual_fields = set(data)
    missing = _REQUIRED_FIELDS - actual_fields
    extra = actual_fields - _REQUIRED_FIELDS
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing: {', '.join(sorted(missing))}")
        if extra:
            details.append(f"unknown: {', '.join(sorted(extra))}")
        raise ValueError(f"Archetype file {path.name} has invalid fields ({'; '.join(details)})")

    slug = _ensure_str(data["slug"], "slug")
    if not re.fullmatch(r"[a-z][a-z0-9\-]*[a-z0-9]", slug):
        raise ValueError(f"Archetype file {path.name}: invalid slug '{slug}'")
    if slug != path.stem:
        raise ValueError(f"Archetype file {path.name}: filename must match slug '{slug}'")

    scope = _ensure_mapping(data["scope"], "scope", _SCOPE_FIELDS)
    authority = _ensure_mapping(data["authority"], "authority", _AUTHORITY_FIELDS)
    return ArchetypeSpec(
        slug=slug,
        name=_ensure_str(data["name"], "name"),
        purpose=_ensure_str(data["purpose"], "purpose"),
        job_to_be_done=_ensure_str(data["job_to_be_done"], "job_to_be_done"),
        outcome=_ensure_str(data["outcome"], "outcome"),
        scope_triggers=_ensure_list(scope["triggers"], "scope.triggers"),
        scope_outputs=_ensure_list(scope["outputs"], "scope.outputs"),
        out_of_scope=_ensure_list(scope["out_of_scope"], "scope.out_of_scope"),
        authority_can_decide=_ensure_list(authority["can_decide"], "authority.can_decide"),
        authority_must_defer=_ensure_list(authority["must_defer"], "authority.must_defer"),
        approval_boundaries=_ensure_str(data["approval_boundaries"], "approval_boundaries"),
        quality_expectations=_ensure_str(data["quality_expectations"], "quality_expectations"),
        evidence_expectations=_ensure_str(data["evidence_expectations"], "evidence_expectations"),
        canonical_skills=_ensure_list(data["canonical_skills"], "canonical_skills"),
    )


def load_archetype_catalog(catalog_dir: Path | None = None) -> Dict[str, ArchetypeSpec]:
    """Load the predefined catalog and validate its declared skill identifiers."""
    directory = catalog_dir or ARCHETYPES_DIR
    if not directory.exists():
        raise FileNotFoundError(f"Archetype catalog directory not found at {directory}")
    catalog: Dict[str, ArchetypeSpec] = {}
    for contract_file in sorted(directory.glob("*.json")):
        spec = _parse_archetype_file(contract_file)
        if spec.slug in catalog:
            raise ValueError(f"Duplicate archetype slug: '{spec.slug}'")
        catalog[spec.slug] = spec
    if not catalog:
        raise ValueError(f"No archetype contract files found in {directory}")
    if catalog_dir is None and set(catalog) != EXPECTED_ARCHETYPE_SLUGS:
        raise ValueError(
            "Default archetype catalog must contain exactly the predefined archetypes: "
            f"{', '.join(sorted(EXPECTED_ARCHETYPE_SLUGS))}"
        )
    for spec in catalog.values():
        validate_skill_assignments(spec.slug, spec.canonical_skills)
    return catalog


def validate_archetype_slugs(slugs: List[str], catalog: Dict[str, ArchetypeSpec]) -> None:
    """Validate that every slug is a known archetype."""
    unknown = [slug for slug in slugs if slug not in catalog]
    if unknown:
        raise ValueError(
            f"Unknown archetype slug(s): {', '.join(unknown)}. "
            f"Available archetypes: {', '.join(sorted(catalog))}"
        )


def validate_skill_assignments(archetype_slug: str, skill_slugs: List[str]) -> None:
    """Validate non-empty, unique, canonical skill identifiers."""
    if not skill_slugs:
        raise ValueError(f"Archetype '{archetype_slug}' must declare at least one canonical skill")
    duplicates = sorted({slug for slug in skill_slugs if skill_slugs.count(slug) > 1})
    if duplicates:
        raise ValueError(
            f"Archetype '{archetype_slug}' declares duplicate canonical skill(s): "
            f"{', '.join(duplicates)}"
        )
    unknown: List[str] = []
    for skill_slug in skill_slugs:
        if not isinstance(skill_slug, str) or not skill_slug.strip():
            raise ValueError(
                f"Archetype '{archetype_slug}' declares an empty canonical skill identifier"
            )
        validate_skill_slug(skill_slug)
        if find_canonical_skill(skill_slug) is None:
            unknown.append(skill_slug)
    if unknown:
        raise ValueError(
            f"Archetype '{archetype_slug}' declares unknown canonical skill(s): "
            f"{', '.join(unknown)}. Skills must exist in workspaces/skills/."
        )


__all__ = [
    "ARCHETYPES_DIR",
    "EXPECTED_ARCHETYPE_SLUGS",
    "ArchetypeSpec",
    "load_archetype_catalog",
    "validate_archetype_slugs",
    "validate_skill_assignments",
]
