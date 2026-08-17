"""Reusable closed JSON / parser primitives and plan schema foundation.

This module is the shared, dependency-light base for strict parsing of the
agent archetype replacement project. It defines:

- ``ValidationError`` and generic scalar/closed-object parsers that reject
  silently-filled defaults, unknown keys, missing keys, wrong scalar types,
  invalid enums, duplicate array members, and non-ASCII bytes.
- Structural (closed-object) parsers for the Section 5 candidate and final
  plan schemas, including the registries, final authority, triggers, and the
  interaction graph. Semantic checks (reachability, conflict symmetry, taint)
  are intentionally out of scope here and belong to later enrichment/validation
  stages.
- The exact Section 4 domain policy literal and its parser.

All names in this file are ASCII. Parsers return either the exact typed value
or raise ``ValidationError`` with a JSON path. They never coerce, sort, fill,
or invent data.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, FrozenSet, List, Optional, Set

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# 17 canonical role slugs (Section 3 of the replacement plan).
CATALOG_SLUGS: FrozenSet[str] = frozenset(
    {
        "role-taker",
        "model",
        "communicator",
        "explainer",
        "knowledge-checker",
        "decision-scaffolder",
        "implicit-reasoner",
        "second-opinion",
        "alternative-perspectives",
        "counterargument",
        "user-aligner",
        "consensus-generator",
        "minority-opinion",
        "formalizer",
        "criteria-applicator",
        "judge",
        "data-processor",
    }
)

SCHEMA_VERSION = "1.0-proposed"

DECISION_CONTROL: FrozenSet[str] = frozenset({"human", "shared", "agent"})
SCOPE: FrozenSet[str] = frozenset({"internal", "external"})
ORIENTATIONS: FrozenSet[str] = frozenset(
    {"none", "check", "independent", "adversarial", "plural", "consensus", "formal", "criteria", "data"}
)
COGNITIVE_MODES: FrozenSet[str] = frozenset(
    {"direct", "model", "scaffold", "implicit", "counterfactual", "formal", "criteria", "compute"}
)
SOCIAL_POSITIONS: FrozenSet[str] = frozenset({"peer", "service", "advocate"})
AGREEMENT_MODES: FrozenSet[str] = frozenset(
    {"none", "align", "second-opinion", "alternatives", "counterargument", "consensus", "minority", "adjudicate"}
)
KNOWLEDGE_MODES: FrozenSet[str] = frozenset({"internal", "external", "either"})
GATE_MODES: FrozenSet[str] = frozenset({"approval", "review", "notification"})
PROFILE_NAMES: FrozenSet[str] = frozenset({"existential", "operational"})
IMPACT_TIERS: FrozenSet[str] = frozenset({"unknown", "high", "medium", "low"})
PROVENANCE_MODES: FrozenSet[str] = frozenset(
    {"internal-model", "external-model", "internal-knowledge", "external-knowledge"}
)

# Legal TriggerId values (Section 3.2 of the replacement plan).
TRIGGER_IDS: FrozenSet[str] = frozenset(
    {
        "high-impact",
        "uncertainty",
        "convergence-risk",
        "recurring",
        "user-requested-challenge",
        "majority-opinion",
        "ai-recommendation-present",
        "conflicting-evidence",
        "ambiguous-ownership",
        "external-model-output-present",
        "explicit-criteria-present",
        "structured-data-present",
        "preference-conflict",
        "consensus-formation",
        "unstated-constraint-suspected",
        "decision-ready-evidence",
    }
)

# ---------------------------------------------------------------------------
# Errors and regex
# ---------------------------------------------------------------------------

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GENERATED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class ValidationError(ValueError):
    """Raised when a closed object or scalar fails strict validation."""


FieldParser = Callable[[object, str], object]


# ---------------------------------------------------------------------------
# Scalar parsers
# ---------------------------------------------------------------------------


def _assert_ascii(value: str, path: str, what: str) -> None:
    if not value.isascii():
        raise ValidationError(f"{path}: {what} must be ASCII")


def as_id(value: object, path: str = "id") -> str:
    if not isinstance(value, str) or not ID_RE.match(value):
        raise ValidationError(f"{path}: invalid Id {value!r}")
    return value


def as_text(value: object, path: str = "text") -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{path}: expected non-empty ASCII string, got {type(value).__name__}")
    if not value.strip():
        raise ValidationError(f"{path}: non-empty string required")
    _assert_ascii(value, path, "text")
    return value.strip()


def as_markdown(value: object, path: str = "markdown") -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{path}: expected non-empty ASCII markdown")
    if "\r" in value:
        raise ValidationError(f"{path}: markdown must not contain CR bytes")
    _assert_ascii(value, path, "markdown")
    return value


def as_path(value: object, path: str = "path") -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{path}: expected non-empty ASCII path")
    _assert_ascii(value, path, "path")
    if value.startswith("/") or "\x00" in value:
        raise ValidationError(f"{path}: path must be relative and contain no NUL: {value!r}")
    if any(segment == ".." for segment in value.split("/")):
        raise ValidationError(f"{path}: path must not contain '..': {value!r}")
    return value


def as_sha256(value: object, path: str = "sha256") -> str:
    if not isinstance(value, str) or not SHA256_RE.match(value):
        raise ValidationError(f"{path}: invalid Sha256 {value!r}")
    return value


def as_nonnegative_int(value: object, path: str = "int") -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{path}: expected JSON integer >= 0")
    if value < 0:
        raise ValidationError(f"{path}: integer must be >= 0")
    return value


def as_boolean(value: object, path: str = "bool") -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{path}: expected JSON boolean")
    return value


def as_enum(value: object, allowed: FrozenSet[str], path: str, what: str) -> str:
    if value not in allowed:
        raise ValidationError(f"{path}: {what} must be one of {sorted(allowed)}, got {value!r}")
    return str(value)


def as_decision_control(value: object, path: str = "decision_control") -> str:
    return as_enum(value, DECISION_CONTROL, path, "DecisionControl")


def as_scope(value: object, path: str = "scope") -> str:
    return as_enum(value, SCOPE, path, "Scope")


def as_generated_at(value: object, path: str = "generated_at") -> str:
    if not isinstance(value, str) or not GENERATED_AT_RE.match(value):
        raise ValidationError(f"{path}: invalid GeneratedAt {value!r}")
    try:
        from datetime import datetime

        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValidationError(f"{path}: impossible calendar/time in GeneratedAt {value!r}") from exc
    return value


def as_role_slug(value: object, path: str = "slug", allowed: FrozenSet[str] = CATALOG_SLUGS) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValidationError(f"{path}: invalid RoleSlug {value!r}")
    return value


# ---------------------------------------------------------------------------
# Closed-object / list helpers
# ---------------------------------------------------------------------------


def _hashable(obj: object) -> str:
    if isinstance(obj, dict):
        return json.dumps(obj, sort_keys=True)
    if isinstance(obj, list):
        return json.dumps(obj, sort_keys=True)
    return repr(obj)


def parse_closed_object(
    data: object,
    *,
    required: Dict[str, FieldParser],
    optional: Optional[Dict[str, FieldParser]] = None,
    path: str = "",
) -> Dict[str, object]:
    """Strictly parse a closed JSON object.

    Every key in ``required`` must be present; no key outside ``required`` and
    ``optional`` is permitted. Returns a dict of parsed values.
    """
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: expected object, got {type(data).__name__}")
    optional = optional or {}
    allowed_keys: Set[str] = set(required) | set(optional)
    actual = set(data)
    missing = set(required) - actual
    unknown = actual - allowed_keys
    if missing:
        raise ValidationError(f"{path}: missing keys {sorted(missing)}")
    if unknown:
        raise ValidationError(f"{path}: unknown keys {sorted(unknown)}")
    result: Dict[str, object] = {}
    for key, parser in required.items():
        result[key] = parser(data[key], f"{path}.{key}" if path else key)
    for key, parser in optional.items():
        if key in data:
            result[key] = parser(data[key], f"{path}.{key}" if path else key)
    return result


def as_unique_list(
    value: object,
    item_parser: FieldParser,
    path: str = "list",
    empty_ok: bool = True,
) -> List[object]:
    if not isinstance(value, list):
        raise ValidationError(f"{path}: expected list, got {type(value).__name__}")
    if not value and not empty_ok:
        raise ValidationError(f"{path}: list must not be empty")
    out: List[object] = []
    seen: Set[str] = set()
    for index, item in enumerate(value):
        parsed = item_parser(item, f"{path}[{index}]")
        key = _hashable(parsed)
        if key in seen:
            raise ValidationError(f"{path}[{index}]: duplicate member")
        seen.add(key)
        out.append(parsed)
    return out


def as_list_of_text(value: object, path: str = "list") -> List[str]:
    return [as_text(item, f"{path}[{i}]") for i, item in _iter_list(value, path)]


def _iter_list(value: object, path: str) -> List[object]:
    if not isinstance(value, list):
        raise ValidationError(f"{path}: expected list, got {type(value).__name__}")
    return list(value)


# ---------------------------------------------------------------------------
# Discriminated / nested record parsers
# ---------------------------------------------------------------------------


def parse_source_identity(data: object, path: str = "source_identity") -> Dict[str, object]:
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: expected object")
    kind = data.get("kind")
    if kind == "agent":
        return parse_closed_object(
            data,
            required={
                "kind": lambda v, p: as_enum(v, frozenset({"agent"}), p, "kind"),
                "id": as_id,
                "disclosure": as_text,
            },
            path=path,
        )
    if kind == "external_system":
        return parse_closed_object(
            data,
            required={
                "kind": lambda v, p: as_enum(v, frozenset({"external_system"}), p, "kind"),
                "id": as_id,
                "disclosure": as_text,
            },
            path=path,
        )
    if kind == "human":
        return parse_closed_object(
            data,
            required={
                "kind": lambda v, p: as_enum(v, frozenset({"human"}), p, "kind"),
                "id": as_id,
                "disclosure": lambda v, p: None if v is None else (_ for _ in ()).throw(
                    ValidationError(f"{path}: human disclosure must be null")
                ),
            },
            path=path,
        )
    if kind == "synthetic_perspective":
        return parse_closed_object(
            data,
            required={
                "kind": lambda v, p: as_enum(v, frozenset({"synthetic_perspective"}), p, "kind"),
                "id": as_id,
            },
            path=path,
        )
    raise ValidationError(f"{path}: unknown SourceIdentity kind {kind!r}")


def parse_context_entry(data: object, path: str = "context_entry") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "key": as_id,
            "content": as_text,
            "sha256": as_sha256,
            "source_identity": parse_source_identity,
        },
        path=path,
    )


def parse_provenance_source(data: object, path: str = "provenance_source") -> Dict[str, object]:
    raw = parse_closed_object(
        data,
        required={
            "id": as_id,
            "label": as_text,
            "path": as_path,
            "sha256": as_sha256,
        },
        path=path,
    )
    if (raw["path"] is None) != (raw["sha256"] is None):
        raise ValidationError(f"{path}: path and sha256 must be both null or both non-null")
    return raw


def parse_provenance_policy(data: object, path: str = "provenance_policy") -> Dict[str, object]:
    raw = parse_closed_object(
        data if isinstance(data, dict) else {},
        required={
            "sources": lambda v, p: as_unique_list(v, parse_provenance_source, p),
        },
        path=path,
    )
    _check_unique_ids(raw["sources"], "provenance_policy.sources", "id")  # type: ignore[arg-type]
    return raw


def parse_human_source(data: object, path: str = "human_source") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={"id": as_id, "label": as_text},
        path=path,
    )


def parse_human_source_registry(data: object, path: str = "human_source_registry") -> Dict[str, object]:
    raw = parse_closed_object(
        data if isinstance(data, dict) else {},
        required={"sources": lambda v, p: as_unique_list(v, parse_human_source, p)},
        path=path,
    )
    _check_unique_ids(raw["sources"], "human_source_registry.sources", "id")  # type: ignore[arg-type]
    return raw


def parse_stakeholder_source_ref(data: object, path: str = "source_ref") -> Dict[str, object]:
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: expected object")
    kind = data.get("kind")
    if kind == "human_source":
        return parse_closed_object(
            data,
            required={
                "kind": lambda v, p: as_enum(v, frozenset({"human_source"}), p, "kind"),
                "source_id": as_id,
            },
            path=path,
        )
    if kind == "profile_evidence":
        return parse_closed_object(
            data,
            required={
                "kind": lambda v, p: as_enum(v, frozenset({"profile_evidence"}), p, "kind"),
                "evidence_id": as_id,
            },
            path=path,
        )
    raise ValidationError(f"{path}: unknown StakeholderSourceRef kind {kind!r}")


def parse_stakeholder(data: object, path: str = "stakeholder") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "id": as_id,
            "label": as_text,
            "source_ref": parse_stakeholder_source_ref,
        },
        path=path,
    )


def parse_stakeholder_registry(data: object, path: str = "stakeholder_registry") -> Dict[str, object]:
    raw = parse_closed_object(
        data if isinstance(data, dict) else {},
        required={"entries": lambda v, p: as_unique_list(v, parse_stakeholder, p)},
        path=path,
    )
    entries = raw["entries"]  # type: ignore[assignment]
    _check_unique_ids(entries, "stakeholder_registry.entries", "id")  # type: ignore[arg-type]
    _check_unique_labels(entries, "stakeholder_registry.entries")  # type: ignore[arg-type]
    return raw


def parse_profile_evidence(data: object, path: str = "profile_evidence") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "id": as_id,
            "profile": lambda v, p: as_enum(v, PROFILE_NAMES, p, "profile"),
            "excerpt": as_text,
            "path": as_path,
            "sha256": as_sha256,
        },
        path=path,
    )


def parse_profile_evidence_registry(data: object, path: str = "profile_evidence_registry") -> Dict[str, object]:
    raw = parse_closed_object(
        data if isinstance(data, dict) else {},
        required={"entries": lambda v, p: as_unique_list(v, parse_profile_evidence, p)},
        path=path,
    )
    entries = raw["entries"]  # type: ignore[assignment]
    _check_unique_ids(entries, "profile_evidence_registry.entries", "id")  # type: ignore[arg-type]
    return raw


def parse_synthetic_perspective(data: object, path: str = "synthetic_perspective") -> Dict[str, object]:
    raw = parse_closed_object(
        data,
        required={
            "id": as_id,
            "label": as_text,
            "disclosure": as_text,
        },
        path=path,
    )
    if "synthetic" not in str(raw["disclosure"]):
        raise ValidationError(f"{path}: disclosure must state it is synthetic")
    return raw


def parse_synthetic_perspective_registry(data: object, path: str = "synthetic_perspective_registry") -> Dict[str, object]:
    raw = parse_closed_object(
        data if isinstance(data, dict) else {},
        required={"entries": lambda v, p: as_unique_list(v, parse_synthetic_perspective, p)},
        path=path,
    )
    entries = raw["entries"]  # type: ignore[assignment]
    _check_unique_ids(entries, "synthetic_perspective_registry.entries", "id")  # type: ignore[arg-type]
    _check_unique_labels(entries, "synthetic_perspective_registry.entries")  # type: ignore[arg-type]
    return raw


def parse_role_assignment(data: object, path: str = "role_assignment") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "slug": as_role_slug,
            "variant": lambda v, p: None if v is None else as_id(v, p),
        },
        path=path,
    )


def parse_calibration(data: object, path: str = "calibration") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "posture": as_text,
            "notes": lambda v, p: as_unique_list(v, as_text, p),
            "constraints": lambda v, p: as_unique_list(v, as_text, p),
        },
        path=path,
    )


def parse_profile_rationale(data: object, path: str = "profile_rationale") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "evidence_refs": lambda v, p: as_unique_list(v, as_id, p),
            "not_applicable": as_boolean,
            "not_applicable_rationale": lambda v, p: None if v is None else as_text(v, p),
            "selection_reason": as_text,
            "calibration_effect": as_text,
        },
        path=path,
    )


def parse_claim_source_ref(data: object, path: str = "claim_source_ref") -> Dict[str, object]:
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: expected object")
    kind = data.get("kind")
    if kind == "provenance_source":
        return parse_closed_object(data, required={"kind": _const("provenance_source"), "source_id": as_id}, path=path)
    if kind == "human_source":
        return parse_closed_object(data, required={"kind": _const("human_source"), "source_id": as_id}, path=path)
    if kind == "context_source":
        return parse_closed_object(data, required={"kind": _const("context_source"), "key": as_id}, path=path)
    if kind == "agent_output":
        return parse_closed_object(
            data,
            required={
                "kind": _const("agent_output"),
                "node_id": as_id,
                "output": as_text,
            },
            path=path,
        )
    raise ValidationError(f"{path}: unknown ClaimSourceRef kind {kind!r}")


def parse_claim_provenance(data: object, path: str = "claim_provenance") -> Optional[Dict[str, object]]:
    if data is None:
        return None
    raw = parse_closed_object(
        data,
        required={
            "mode": lambda v, p: as_enum(v, KNOWLEDGE_MODES, p, "mode"),
            "sources": lambda v, p: as_unique_list(v, parse_claim_source_ref, p),
            "unsupported_label": as_text,
            "citations": lambda v, p: as_unique_list(v, as_text, p),
        },
        path=path,
    )
    if raw["mode"] == "external" and not raw["citations"]:
        raise ValidationError(f"{path}: external mode requires non-empty citations")
    return raw


def parse_resolved_settings(data: object, path: str = "resolved_design_settings") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "decision_control": as_decision_control,
            "knowledge": lambda v, p: parse_closed_object(
                v,
                required={
                    "mode": lambda w, q: as_enum(w, KNOWLEDGE_MODES, q, "mode"),
                    "provenance_required": as_boolean,
                    "citations_required_for_external": as_boolean,
                },
                path=p,
            ),
            "verification_diversity": lambda v, p: parse_closed_object(
                v,
                required={
                    "orientation": lambda w, q: as_enum(w, ORIENTATIONS, q, "orientation"),
                    "obligations": lambda w, q: as_unique_list(w, as_text, q),
                },
                path=p,
            ),
            "cognitive": lambda v, p: parse_closed_object(
                v,
                required={
                    "modes": lambda w, q: as_unique_list(w, lambda x, r: as_enum(x, COGNITIVE_MODES, r, "mode"), q),
                    "forcing_triggers": lambda w, q: as_unique_list(w, as_id, q),
                },
                path=p,
            ),
            "social_positions_by_role": _parse_role_position_map,
            "group": lambda v, p: parse_closed_object(
                v,
                required={
                    "group_facing": as_boolean,
                    "independence_required": as_boolean,
                    "source_disclosure_required": as_boolean,
                    "consensus_requirements": lambda w, q: as_unique_list(w, as_text, q),
                },
                path=p,
            ),
            "agreement_disagreement": lambda v, p: parse_closed_object(
                v,
                required={
                    "modes": lambda w, q: as_unique_list(w, lambda x, r: as_enum(x, AGREEMENT_MODES, r, "mode"), q),
                    "required_triggers": lambda w, q: as_unique_list(w, as_id, q),
                },
                path=p,
            ),
        },
        path=path,
    )


def _parse_role_position_map(value: object, path: str) -> Dict[str, object]:
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: expected object mapping RoleSlug -> position")
    out: Dict[str, object] = {}
    for key, val in value.items():
        out[as_role_slug(key, f"{path} key")] = as_enum(val, SOCIAL_POSITIONS, f"{path}.{key}", "position")
    return out


def parse_action_ref(data: object, path: str = "action_ref") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "role_slug": as_role_slug,
            "action_id": as_id,
        },
        path=path,
    )


def _candidate_fields() -> Dict[str, FieldParser]:
    return {
        "id": as_id,
        "primary_role": parse_role_assignment,
        "secondary_roles": lambda v, p: as_unique_list(v, parse_role_assignment, p),
        "profile_rationale": parse_profile_rationale,
        "calibration": parse_calibration,
        "skills": lambda v, p: as_unique_list(v, as_id, p),
        "resolved_design_settings": parse_resolved_settings,
        "claim_provenance": parse_claim_provenance,
        "graph_participation": lambda v, p: parse_closed_object(v, required={"node_id": as_id}, path=p),
    }


def parse_candidate_agent(
    data: object,
    path: str = "candidate_agent",
    optional: Optional[Dict[str, FieldParser]] = None,
) -> Dict[str, object]:
    raw = parse_closed_object(
        data,
        required=_candidate_fields(),
        optional=optional,
        path=path,
    )
    secondary = raw["secondary_roles"]  # type: ignore[assignment]
    if len(secondary) > 3:
        raise ValidationError(f"{path}: at most three secondary roles allowed")
    return raw


def parse_hash_ref(data: object, path: str = "hash_ref") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={"path": as_path, "sha256": as_sha256},
        path=path,
    )


def parse_generation_provenance(data: object, path: str = "generation_provenance") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "selection_prompt": parse_hash_ref,
            "soul_prompt": parse_hash_ref,
            "interaction_posture": parse_hash_ref,
            "role_catalogs": lambda v, p: as_unique_list(
                v,
                lambda w, q: parse_closed_object(
                    w,
                    required={"slug": as_role_slug, "path": as_path, "sha256": as_sha256},
                    path=q,
                ),
                p,
            ),
            "skill_files": lambda v, p: as_unique_list(
                v,
                lambda w, q: parse_closed_object(
                    w,
                    required={"slug": as_id, "path": as_path, "sha256": as_sha256},
                    path=q,
                ),
                p,
            ),
            "model_provider": as_text,
        },
        path=path,
    )


def parse_planned_agent(data: object, path: str = "planned_agent") -> Dict[str, object]:
    required = dict(_candidate_fields())
    required.update(
        {
            "social_positions_by_role": _parse_role_position_map,
            "role_scoped_authority": _parse_role_scoped_authority,
            "soul_markdown": as_markdown,
            "generation_provenance": parse_generation_provenance,
        }
    )
    raw = parse_closed_object(data, required=required, path=path)
    secondary = raw["secondary_roles"]  # type: ignore[assignment]
    if len(secondary) > 3:
        raise ValidationError(f"{path}: at most three secondary roles allowed")
    return raw


def _parse_role_scoped_authority(value: object, path: str) -> Dict[str, object]:
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: expected object mapping RoleSlug -> authority entry")
    out: Dict[str, object] = {}
    for key, val in value.items():
        role = as_role_slug(key, f"{path} key")
        out[role] = parse_closed_object(
            val,
            required={
                "actions": lambda w, q: as_unique_list(w, parse_action_ref, q),
                "prohibited_action_ids": lambda w, q: as_unique_list(w, as_id, q),
            },
            path=f"{path}.{key}",
        )
    return out


def parse_domain_assessment(data: object, path: str = "domain_assessment") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "tier": lambda v, p: as_enum(v, IMPACT_TIERS, p, "tier"),
            "evidence": lambda v, p: as_unique_list(v, as_text, p),
        },
        path=path,
    )


def parse_final_authority(data: object, path: str = "final_authority") -> Dict[str, object]:
    raw = parse_closed_object(
        data,
        required={
            "agent_id": lambda v, p: None if v is None else as_id(v, p),
            "action_refs": lambda v, p: as_unique_list(v, parse_action_ref, p),
            "domain_scope": as_text,
            "decision_control": as_decision_control,
            "terminal_gate_id": as_id,
            "rationale": as_text,
        },
        path=path,
    )
    if raw["agent_id"] is None:
        if raw["action_refs"]:
            raise ValidationError(f"{path}: null agent_id requires empty action_refs")
        if raw["decision_control"] != "human":
            raise ValidationError(f"{path}: null agent_id requires decision_control 'human'")
    return raw


def parse_trigger_evaluation(data: object, path: str = "trigger_evaluation") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "trigger_id": as_id,
            "evidence_refs": lambda v, p: as_unique_list(v, parse_evidence_ref, p),
            "result": as_boolean,
            "rationale": as_text,
        },
        path=path,
    )


def parse_evidence_ref(data: object, path: str = "evidence_ref") -> Dict[str, object]:
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: expected object")
    kind = data.get("kind")
    if kind == "context":
        return parse_closed_object(data, required={"kind": _const("context"), "key": as_id}, path=path)
    if kind == "profile":
        return parse_closed_object(data, required={"kind": _const("profile"), "evidence_id": as_id}, path=path)
    if kind == "domain_assessment":
        return parse_closed_object(
            data,
            required={"kind": _const("domain_assessment"), "index": as_nonnegative_int},
            path=path,
        )
    if kind == "node_output":
        return parse_closed_object(
            data,
            required={"kind": _const("node_output"), "node_id": as_id, "output": as_text},
            path=path,
        )
    raise ValidationError(f"{path}: unknown EvidenceRef kind {kind!r}")


def parse_typed_input_ref(data: object, path: str = "typed_input_ref") -> Dict[str, object]:
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: expected object")
    kind = data.get("kind")
    if kind == "context":
        return parse_closed_object(data, required={"kind": _const("context"), "key": as_id}, path=path)
    if kind == "node_output":
        return parse_closed_object(
            data,
            required={"kind": _const("node_output"), "node_id": as_id, "output": as_text},
            path=path,
        )
    if kind == "external_source":
        return parse_closed_object(data, required={"kind": _const("external_source"), "source_id": as_id}, path=path)
    raise ValidationError(f"{path}: unknown TypedInputRef kind {kind!r}")


def parse_agent_node(data: object, path: str = "agent_node") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "id": as_id,
            "kind": lambda v, p: as_enum(v, frozenset({"agent"}), p, "kind"),
            "agent_id": as_id,
            "role": as_role_slug,
            "visible_inputs": lambda v, p: as_unique_list(v, parse_typed_input_ref, p),
            "source_identity": parse_source_identity,
            "phase": as_nonnegative_int,
            "exec_group": as_text,
            "declared_outputs": lambda v, p: as_unique_list(v, as_text, p),
        },
        path=path,
    )


def parse_human_gate_node(data: object, path: str = "human_gate_node") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "id": as_id,
            "kind": lambda v, p: as_enum(v, frozenset({"human_gate"}), p, "kind"),
            "mode": lambda v, p: as_enum(v, GATE_MODES, p, "mode"),
            "condition": as_text,
            "decision_owner": as_text,
            "required_inputs": lambda v, p: as_unique_list(v, parse_typed_input_ref, p),
            "continuation": lambda v, p: as_enum(v, frozenset({"end"}), p, "continuation"),
            "phase": as_nonnegative_int,
        },
        path=path,
    )


def parse_interaction_graph(data: object, path: str = "interaction_graph") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "nodes": lambda v, p: as_unique_list(v, _parse_graph_node, p),
            "edges": lambda v, p: as_unique_list(
                v,
                lambda w, q: parse_closed_object(
                    w,
                    required={
                        "from": as_id,
                        "to": as_id,
                        "kind": lambda x, r: as_enum(x, frozenset({"sequential", "parallel"}), r, "kind"),
                        "handoff": as_text,
                    },
                    path=q,
                ),
                p,
            ),
            "independent_opinion_boundaries": lambda v, p: as_unique_list(
                v,
                lambda w, q: parse_closed_object(
                    w,
                    required={
                        "isolated_agent_ids": lambda x, r: as_unique_list(x, as_id, r),
                        "blocked_node_outputs": lambda x, r: as_unique_list(
                            x,
                            lambda y, s: parse_closed_object(
                                y, required={"node_id": as_id, "output": as_text}, path=s
                            ),
                            r,
                        ),
                        "release_phase": as_nonnegative_int,
                    },
                    path=q,
                ),
                p,
            ),
            "aggregation": lambda v, p: as_unique_list(
                v,
                lambda w, q: parse_closed_object(
                    w,
                    required={
                        "id": as_id,
                        "aggregator_node_id": as_id,
                        "inputs": lambda x, r: as_unique_list(x, parse_typed_input_ref, r),
                        "output": as_text,
                        "destination_gate_id": as_id,
                        "preserve_unresolved_disagreement": as_boolean,
                    },
                    path=q,
                ),
                p,
            ),
            "unresolved_disagreement": _parse_unresolved_disagreement,
        },
        path=path,
    )


def _parse_graph_node(data: object, path: str) -> Dict[str, object]:
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: expected object")
    kind = data.get("kind")
    if kind == "agent":
        return parse_agent_node(data, path)
    if kind == "human_gate":
        return parse_human_gate_node(data, path)
    raise ValidationError(f"{path}: unknown graph node kind {kind!r}")


def _parse_unresolved_disagreement(data: object, path: str) -> Dict[str, object]:
    raw = parse_closed_object(
        data,
        required={
            "triggered": as_boolean,
            "reason": lambda v, p: None if v is None else as_text(v, p),
            "gate_id": lambda v, p: None if v is None else as_id(v, p),
            "output": _parse_output_ref_or_null,
        },
        path=path,
    )
    triggered = raw["triggered"]
    has_reason = raw["reason"] is not None
    has_gate = raw["gate_id"] is not None
    has_output = raw["output"] is not None
    if triggered and not (has_reason and has_gate and has_output):
        raise ValidationError(f"{path}: triggered disagreement requires reason, gate_id, and output")
    if (not triggered) and (has_reason or has_gate or has_output):
        raise ValidationError(f"{path}: non-triggered disagreement must have null reason/gate/output")
    return raw


def _parse_output_ref_or_null(data: object, path: str) -> Optional[Dict[str, object]]:
    if data is None:
        return None
    return parse_closed_object(
        data,
        required={"node_id": as_id, "output": as_text},
        path=path,
    )


def parse_interaction_posture_snapshot(data: object, path: str = "interaction_posture") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={"path": as_path, "sha256": as_sha256, "markdown": as_markdown},
        path=path,
    )


def parse_projection_hashes(data: object, path: str = "projection_hashes") -> Dict[str, object]:
    return parse_closed_object(
        data,
        required={
            "persona_map": as_sha256,
            "agents": lambda v, p: as_unique_list(
                v,
                lambda w, q: parse_closed_object(
                    w,
                    required={"agent_id": as_id, "path": as_path, "sha256": as_sha256},
                    path=q,
                ),
                p,
            ),
        },
        path=path,
    )


# ---------------------------------------------------------------------------
# Top-level plan schemas
# ---------------------------------------------------------------------------


def _candidate_common() -> Dict[str, FieldParser]:
    return {
        "schema_version": lambda v, p: _const_value(v, "1.0-proposed", p),
        "context_registry": parse_context_registry,
        "human_source_registry": parse_human_source_registry,
        "stakeholder_registry": parse_stakeholder_registry,
        "profile_evidence_registry": parse_profile_evidence_registry,
        "synthetic_perspective_registry": parse_synthetic_perspective_registry,
        "domain_assessment": parse_domain_assessment,
        "provenance_policy": parse_provenance_policy,
        "agents": lambda v, p: as_unique_list(v, parse_candidate_agent, p, empty_ok=False),
        "final_authority": parse_final_authority,
        "trigger_evaluations": lambda v, p: as_unique_list(v, parse_trigger_evaluation, p),
        "interaction_graph": parse_interaction_graph,
    }


def parse_context_registry(data: object, path: str = "context_registry") -> Dict[str, object]:
    raw = parse_closed_object(
        data if isinstance(data, dict) else {},
        required={"entries": lambda v, p: as_unique_list(v, parse_context_entry, p)},
        path=path,
    )
    _check_unique_ids(raw["entries"], "context_registry.entries", "key")  # type: ignore[arg-type]
    return raw


def parse_candidate_agent_plan(data: object, path: str = "") -> Dict[str, object]:
    return parse_closed_object(data, required=_candidate_common(), path=path or "candidate_agent_plan")


def parse_agent_plan(data: object, path: str = "") -> Dict[str, object]:
    common = _candidate_common()
    common["agents"] = lambda v, p: as_unique_list(v, parse_planned_agent, p, empty_ok=False)
    common["generated_at"] = as_generated_at
    common["domain_policy_ref"] = parse_hash_ref
    common["interaction_posture"] = parse_interaction_posture_snapshot
    common["projection_hashes"] = parse_projection_hashes
    return parse_closed_object(data, required=common, path=path or "agent_plan")


def validate_candidate_plan(data: object) -> Dict[str, object]:
    """Strictly validate a CandidateAgentPlan; return the parsed structure."""
    return parse_candidate_agent_plan(data)


def validate_agent_plan(data: object) -> Dict[str, object]:
    """Strictly validate an AgentPlan; return the parsed structure."""
    return parse_agent_plan(data)


# ---------------------------------------------------------------------------
# Domain policy (Section 4)
# ---------------------------------------------------------------------------

DEFAULT_DOMAIN_POLICY: Dict[str, object] = {
    "schema_version": "1.0-proposed",
    "decision_control_rank": {"human": 0, "shared": 1, "agent": 2},
    "impact_tiers": {
        "unknown": {
            "decision_control_levels": ["human"],
            "default_decision_control": "human",
            "terminal_gate_modes": ["approval"],
            "default_terminal_gate_mode": "approval",
            "within_system_final_decision": False,
        },
        "high": {
            "decision_control_levels": ["human"],
            "default_decision_control": "human",
            "terminal_gate_modes": ["approval"],
            "default_terminal_gate_mode": "approval",
            "within_system_final_decision": False,
        },
        "medium": {
            "decision_control_levels": ["human", "shared"],
            "default_decision_control": "human",
            "terminal_gate_modes": ["approval", "review"],
            "default_terminal_gate_mode": "approval",
            "within_system_final_decision": True,
        },
        "low": {
            "decision_control_levels": ["human", "shared", "agent"],
            "default_decision_control": "agent",
            "terminal_gate_modes": ["approval", "review", "notification"],
            "default_terminal_gate_mode": "notification",
            "within_system_final_decision": True,
        },
    },
}


def parse_domain_policy(data: object, path: str = "domain_policy") -> Dict[str, object]:
    raw = parse_closed_object(
        data,
        required={
            "schema_version": lambda v, p: _const_value(v, "1.0-proposed", p),
            "decision_control_rank": lambda v, p: parse_closed_object  # placeholder replaced below
            if False
            else _parse_decision_control_rank(v, p),
            "impact_tiers": _parse_impact_tiers,
        },
        path=path,
    )
    if raw != DEFAULT_DOMAIN_POLICY:
        raise ValidationError(f"{path}: domain policy must equal the exact Section 4 literal")
    return raw


def _parse_decision_control_rank(value: object, path: str) -> Dict[str, object]:
    raw = parse_closed_object(
        value,
        required={
            "human": lambda v, p: as_nonnegative_int(v, p),
            "shared": lambda v, p: as_nonnegative_int(v, p),
            "agent": lambda v, p: as_nonnegative_int(v, p),
        },
        path=path,
    )
    if raw != {"human": 0, "shared": 1, "agent": 2}:
        raise ValidationError(f"{path}: decision_control_rank must be exactly human=0, shared=1, agent=2")
    return raw


def _parse_impact_tiers(value: object, path: str) -> Dict[str, object]:
    if not isinstance(value, dict) or set(value) != set(IMPACT_TIERS):
        raise ValidationError(f"{path}: impact_tiers must contain exactly {sorted(IMPACT_TIERS)}")
    out: Dict[str, object] = {}
    for tier in IMPACT_TIERS:
        out[tier] = parse_closed_object(
            value[tier],
            required={
                "decision_control_levels": lambda v, p: as_unique_list(
                    v, lambda x, q: as_enum(x, DECISION_CONTROL, q, "level"), p, empty_ok=False
                ),
                "default_decision_control": as_decision_control,
                "terminal_gate_modes": lambda v, p: as_unique_list(
                    v, lambda x, q: as_enum(x, GATE_MODES, q, "gate mode"), p, empty_ok=False
                ),
                "default_terminal_gate_mode": lambda v, p: as_enum(v, GATE_MODES, p, "gate mode"),
                "within_system_final_decision": as_boolean,
            },
            path=f"{path}.{tier}",
        )
    return out


def load_domain_policy(path: Optional[Path] = None) -> Dict[str, object]:
    """Load and strictly validate ``profiles/alignment/domain_policy.json``."""
    target = path or (Path(__file__).resolve().parent.parent / "profiles" / "alignment" / "domain_policy.json")
    if not target.exists():
        raise FileNotFoundError(f"Domain policy not found at {target}")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{target}: invalid JSON: {exc}") from None
    return parse_domain_policy(data)


# ---------------------------------------------------------------------------
# Small parser helpers
# ---------------------------------------------------------------------------


def _const(expected: str) -> FieldParser:
    def parser(value: object, path: str) -> str:
        if value != expected:
            raise ValidationError(f"{path}: kind must be {expected!r}, got {value!r}")
        return str(value)

    return parser


def _const_value(value: object, expected: str, path: str) -> str:
    if value != expected:
        raise ValidationError(f"{path}: must equal {expected!r}, got {value!r}")
    return str(value)


def _check_unique_ids(entries: List[object], path: str, id_key: str) -> None:
    seen: Set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or id_key not in entry:
            raise ValidationError(f"{path}: entry missing {id_key}")
        key = entry[id_key]
        if not isinstance(key, str):
            raise ValidationError(f"{path}: {id_key} must be string")
        if key in seen:
            raise ValidationError(f"{path}: duplicate {id_key} {key!r}")
        seen.add(key)


def _check_unique_labels(entries: List[object], path: str) -> None:
    seen: Set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or "label" not in entry:
            raise ValidationError(f"{path}: entry missing label")
        label = entry["label"]
        if not isinstance(label, str):
            raise ValidationError(f"{path}: label must be string")
        if label in seen:
            raise ValidationError(f"{path}: duplicate label {label!r}")
        seen.add(label)


# ---------------------------------------------------------------------------
# Deterministic enrichment and final-plan semantic validation
# ---------------------------------------------------------------------------

import hashlib  # noqa: E402

DECISION_RANK: Dict[str, int] = {"human": 0, "shared": 1, "agent": 2}


def sha256_text(text: str) -> str:
    """Return the lowercase hex sha256 of the UTF-8 bytes of ``text``."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _active_role_slugs(agent: Dict[str, object]) -> List[str]:
    primary = agent["primary_role"]  # type: ignore[assignment]
    slugs = [primary["slug"]]  # type: ignore[index]
    for sec in agent["secondary_roles"]:  # type: ignore[assignment]
        slugs.append(sec["slug"])  # type: ignore[index]
    return slugs


def derive_social_positions(agent: Dict[str, object], catalog: Dict[str, dict]) -> Dict[str, str]:
    """One social position per active role: role_override else default_position."""
    out: Dict[str, str] = {}
    for slug in _active_role_slugs(agent):
        spec = catalog[slug]
        position = spec["social"]["role_override"] or spec["social"]["default_position"]
        out[slug] = position  # type: ignore[assignment]
    return out


def recompute_resolved_settings(
    agent: Dict[str, object],
    catalog: Dict[str, dict],
    domain_tier: Dict[str, object],
) -> Dict[str, object]:
    """Recompute the seven-dimension resolved settings deterministically."""
    specs = [catalog[s] for s in _active_role_slugs(agent)]
    primary = specs[0]

    # decision_control: intersection of role allowed sets and tier levels.
    allowed = set(primary["decision_control"]["allowed"])
    for s in specs[1:]:
        allowed &= set(s["decision_control"]["allowed"])
    allowed &= set(domain_tier["decision_control_levels"])  # type: ignore[arg-type]
    if not allowed:
        raise ValidationError(
            "agent settings: empty decision_control intersection across active roles/tier"
        )
    primary_default = primary["decision_control"]["default"]
    if primary_default in allowed:
        dc = primary_default
    else:
        dc = min(allowed, key=lambda x: DECISION_RANK[x])

    # knowledge: intersect modes; OR booleans.
    kmodes = set(primary["knowledge"]["allowed_modes"])
    for s in specs[1:]:
        kmodes &= set(s["knowledge"]["allowed_modes"])
    if not kmodes:
        raise ValidationError("agent settings: empty knowledge mode intersection")
    kdefault = primary["knowledge"]["default_mode"]
    kmode = kdefault if kdefault in kmodes else sorted(kmodes)[0]
    provenance_required = any(s["knowledge"]["provenance_required"] for s in specs)
    citations = any(s["knowledge"]["citations_required_for_external"] for s in specs)

    # verification_diversity: primary orientation; union obligations.
    vorientation = primary["verification_diversity"]["orientation"]
    vobligations = _union(s["verification_diversity"]["obligations"] for s in specs)

    # cognitive: union modes and triggers.
    cmodes = _union(s["cognitive"]["supported_modes"] for s in specs)
    ctriggers = _union(s["cognitive"]["forcing_triggers"] for s in specs)

    # group: OR booleans; union requirements.
    group_facing = any(s["group"]["group_facing"] for s in specs)
    independence = any(s["group"]["independence_required"] for s in specs)
    disclosure = any(s["group"]["source_disclosure_required"] for s in specs)
    consensus = _union(s["group"]["consensus_requirements"] for s in specs)

    # agreement_disagreement: union modes and triggers.
    amodes = _union(s["agreement_disagreement"]["supported_modes"] for s in specs)
    atriggers = _union(s["agreement_disagreement"]["required_triggers"] for s in specs)

    social = derive_social_positions(agent, catalog)
    return {
        "decision_control": dc,
        "knowledge": {
            "mode": kmode,
            "provenance_required": provenance_required,
            "citations_required_for_external": citations,
        },
        "verification_diversity": {"orientation": vorientation, "obligations": vobligations},
        "cognitive": {"modes": cmodes, "forcing_triggers": ctriggers},
        "social_positions_by_role": social,
        "group": {
            "group_facing": group_facing,
            "independence_required": independence,
            "source_disclosure_required": disclosure,
            "consensus_requirements": consensus,
        },
        "agreement_disagreement": {"modes": amodes, "required_triggers": atriggers},
    }


def derive_role_scoped_authority(
    agent: Dict[str, object], catalog: Dict[str, dict]
) -> Dict[str, object]:
    """Build the per-active-role authority map from catalog actions."""
    out: Dict[str, object] = {}
    for slug in _active_role_slugs(agent):
        spec = catalog[slug]
        out[slug] = {
            "actions": [
                {"role_slug": slug, "action_id": a["id"]} for a in spec["authority"]["actions"]
            ],
            "prohibited_action_ids": list(spec["authority"]["prohibited_action_ids"]),
        }
    return out


def _union(iterables: object) -> List[str]:
    seen: List[str] = []
    for it in iterables:  # type: ignore[attr-defined]
        for item in it:
            if item not in seen:
                seen.append(item)
    return seen


def enrich_candidate_to_planned(
    candidate: Dict[str, object],
    catalog: Dict[str, dict],
    domain_policy: Dict[str, object],
    *,
    posture_snapshot: Dict[str, object],
    generation_provenance: Dict[str, object],
    domain_policy_ref: Dict[str, object],
    generated_at: str,
    soul_markdown_by_id: Dict[str, str],
) -> Dict[str, object]:
    """Deterministically enrich a validated CandidateAgentPlan into an AgentPlan.

    The function does not invent model values: role settings, social maps, and
    the role-scoped authority are recomputed from the catalog and domain policy.
    The single final-authority effective control, when non-null and valid, is
    persisted as the holder agent's resolved decision control.
    """
    tier_name = candidate["domain_assessment"]["tier"]  # type: ignore[assignment]
    tier = domain_policy["impact_tiers"][tier_name]  # type: ignore[assignment,index]

    planned_agents: List[Dict[str, object]] = []
    for agent in candidate["agents"]:  # type: ignore[assignment]
        settings = recompute_resolved_settings(agent, catalog, tier)  # type: ignore[arg-type]
        social = derive_social_positions(agent, catalog)
        authority = derive_role_scoped_authority(agent, catalog)
        planned = dict(agent)  # type: ignore[arg-type]
        planned["social_positions_by_role"] = social
        planned["role_scoped_authority"] = authority
        # Resolved settings carry the social map too (closed object).
        settings["social_positions_by_role"] = social
        planned["resolved_design_settings"] = settings
        if agent["id"] not in soul_markdown_by_id:  # type: ignore[index]
            raise ValidationError(f"agent {agent['id']} has no generated soul markdown")  # type: ignore[index]
        planned["soul_markdown"] = soul_markdown_by_id[agent["id"]]  # type: ignore[index]
        planned["generation_provenance"] = generation_provenance
        planned_agents.append(planned)

    final_authority = candidate["final_authority"]  # type: ignore[assignment]
    if final_authority["agent_id"] is not None:  # type: ignore[index]
        holder_id = final_authority["agent_id"]  # type: ignore[index]
        holder = next((a for a in planned_agents if a["id"] == holder_id), None)
        if holder is None:
            raise ValidationError(f"final_authority.agent_id '{holder_id}' has no matching agent")
        holder["resolved_design_settings"]["decision_control"] = final_authority["decision_control"]  # type: ignore[index]

    plan = dict(candidate)  # type: ignore[assignment]
    plan["agents"] = planned_agents
    plan["generated_at"] = generated_at
    plan["domain_policy_ref"] = domain_policy_ref
    plan["interaction_posture"] = posture_snapshot
    return plan


def compute_projection_hashes(rendered: Dict[str, str], plan: Dict[str, object]) -> Dict[str, object]:
    """Compute byte-exact projection hashes from rendered projection content.

    ``rendered`` maps a relative projection path (e.g. ``agents/a1.md``) to its
    exact content. Returns the ``ProjectionHashes`` closed object.
    """
    persona_content = rendered.get("persona_map.md")
    if persona_content is None:
        raise ValidationError("projection_hashes: persona_map.md content missing")
    agents_hashes: List[Dict[str, object]] = []
    for agent in plan["agents"]:  # type: ignore[assignment]
        rel = f"agents/{agent['id']}.md"  # type: ignore[index]
        if rel not in rendered:
            raise ValidationError(f"projection_hashes: missing rendered content for {rel}")
        agents_hashes.append(
            {"agent_id": agent["id"], "path": rel, "sha256": sha256_text(rendered[rel])}  # type: ignore[index]
        )
    return {
        "persona_map": sha256_text(persona_content),
        "agents": agents_hashes,
    }


def validate_agent_plan_semantics(
    plan: Dict[str, object],
    catalog: Dict[str, dict],
    domain_policy: Dict[str, object],
) -> None:
    """Validate final-plan semantics beyond the closed structural parse.

    Covers posture snapshot hash, recomputed role settings, derived social map
    and role-scoped authority, composition, skills, the singular final authority
    effective-control rule, provenance registries, and graph DAG/gate/trigger
    basics. Raises ``ValidationError`` on the first violation.
    """
    tier_name = plan["domain_assessment"]["tier"]  # type: ignore[assignment]
    if tier_name not in domain_policy["impact_tiers"]:  # type: ignore[assignment]
        raise ValidationError(f"domain tier '{tier_name}' absent from domain policy")
    tier = domain_policy["impact_tiers"][tier_name]  # type: ignore[assignment,index]

    _validate_posture_snapshot(plan["interaction_posture"])  # type: ignore[arg-type]

    by_id = {a["id"]: a for a in plan["agents"]}  # type: ignore[assignment,index]
    final_authority = plan["final_authority"]  # type: ignore[assignment]

    for agent in plan["agents"]:  # type: ignore[assignment]
        _validate_agent_semantics(agent, catalog, tier, plan, by_id, final_authority)  # type: ignore[arg-type]

    _validate_final_authority(final_authority, plan, catalog, tier, by_id)  # type: ignore[arg-type]
    _validate_graph(plan, tier, catalog)  # type: ignore[arg-type]


def _validate_posture_snapshot(posture: Dict[str, object]) -> None:
    markdown = posture["markdown"]  # type: ignore[index]
    expected = posture["sha256"]  # type: ignore[index]
    actual = sha256_text(markdown)
    if actual != expected:
        raise ValidationError(
            f"interaction_posture sha256 mismatch: expected {expected}, got {actual}"
        )
    if not isinstance(markdown, str) or not markdown.isascii():
        raise ValidationError("interaction_posture markdown must be ASCII")


def _validate_agent_semantics(
    agent: Dict[str, object],
    catalog: Dict[str, dict],
    tier: Dict[str, object],
    plan: Dict[str, object],
    by_id: Dict[str, object],
    final_authority: Dict[str, object],
) -> None:
    slugs = _active_role_slugs(agent)
    for slug in slugs:
        if slug not in catalog:
            raise ValidationError(f"agent {agent['id']}: unknown active role {slug}")  # type: ignore[index]

    # Variant resolution.
    primary = agent["primary_role"]  # type: ignore[assignment]
    if primary["variant"] is not None:  # type: ignore[index]
        variants = [v["id"] for v in catalog[primary["slug"]]["variants"]]  # type: ignore[index]
        if primary["variant"] not in variants:  # type: ignore[index]
            raise ValidationError(
                f"agent {agent['id']}: variant {primary['variant']} not in role {primary['slug']}"  # type: ignore[index]
            )

    # Composition: max secondaries, conflicts, primary compatibility, prerequisites.
    secondaries = agent["secondary_roles"]  # type: ignore[assignment]
    if len(secondaries) > 3:
        raise ValidationError(f"agent {agent['id']}: more than three secondary roles")  # type: ignore[index]
    primary_spec = catalog[primary["slug"]]  # type: ignore[index]
    compatible = set(primary_spec["composition"]["primary_compatible_secondary"])
    conflicts = set(primary_spec["composition"]["conflicts"])
    active_set = set(slugs)
    for sec in secondaries:
        sec_slug = sec["slug"]  # type: ignore[index]
        if sec_slug not in compatible:
            raise ValidationError(
                f"agent {agent['id']}: secondary {sec_slug} not compatible with primary {primary['slug']}"  # type: ignore[index]
            )
        if sec_slug in conflicts:
            raise ValidationError(
                f"agent {agent['id']}: secondary {sec_slug} conflicts with primary {primary['slug']}"  # type: ignore[index]
            )
        sec_spec = catalog[sec_slug]
        if primary["slug"] in set(sec_spec["composition"]["conflicts"]):  # type: ignore[index]
            raise ValidationError(
                f"agent {agent['id']}: symmetric conflict between {primary['slug']} and {sec_slug}"  # type: ignore[index]
            )
    # Prerequisite groups: outer-OR, inner-AND.
    for slug in slugs:
        spec = catalog[slug]
        groups = spec["composition"]["prerequisite_groups"]
        if groups and not any(
            _prereq_group_passes(group, agent, plan, catalog) for group in groups
        ):
            raise ValidationError(f"agent {agent['id']}: role {slug} prerequisite groups unsatisfied")  # type: ignore[index]

    # Skills resolve in the active roles' canonical skill sets.
    skill_union = set()
    for slug in slugs:
        skill_union |= set(catalog[slug]["canonical_skills"])
    for skill in agent["skills"]:  # type: ignore[assignment]
        if skill not in skill_union:
            raise ValidationError(f"agent {agent['id']}: skill {skill} not in active role canonical skills")  # type: ignore[index]

    # Recomputed settings must equal the stored resolved settings.
    recomputed = recompute_resolved_settings(agent, catalog, tier)  # type: ignore[arg-type]
    if final_authority["agent_id"] == agent["id"]:  # type: ignore[index]
        recomputed = dict(recomputed)  # type: ignore[assignment]
        recomputed["decision_control"] = final_authority["decision_control"]  # type: ignore[index]
    stored = agent["resolved_design_settings"]  # type: ignore[assignment]
    if recomputed != stored:
        raise ValidationError(f"agent {agent['id']}: resolved settings do not match recomputation")

    # Derived social map and role-scoped authority must equal stored values.
    if derive_social_positions(agent, catalog) != agent.get("social_positions_by_role"):
        raise ValidationError(f"agent {agent['id']}: social_positions_by_role mismatch")
    if derive_role_scoped_authority(agent, catalog) != agent.get("role_scoped_authority"):
        raise ValidationError(f"agent {agent['id']}: role_scoped_authority mismatch")

    # Final authority holder override persisted identically.
    if final_authority["agent_id"] == agent["id"]:  # type: ignore[index]
        if stored["decision_control"] != final_authority["decision_control"]:  # type: ignore[index]
            raise ValidationError(
                f"agent {agent['id']}: holder resolved decision_control must equal final authority decision_control"  # type: ignore[index]
            )


def _prereq_group_passes(group: List[object], agent: Dict[str, object], plan: Dict[str, object], catalog: Dict[str, dict]) -> bool:
    context_keys = {e["key"] for e in plan["context_registry"]["entries"]}  # type: ignore[assignment,index]
    profile_names = {e["profile"] for e in plan["profile_evidence_registry"]["entries"]}  # type: ignore[assignment,index]
    active = set(_active_role_slugs(agent))
    visible_inputs = set()
    for node in plan["interaction_graph"]["nodes"]:  # type: ignore[assignment]
        if node["kind"] == "agent" and node["agent_id"] == agent["id"]:  # type: ignore[index]
            for ref in node["visible_inputs"]:  # type: ignore[index]
                if ref["kind"] == "context":  # type: ignore[index]
                    visible_inputs.add(ref["key"])  # type: ignore[index]
    role_inputs = set()
    for slug in active:
        role_inputs |= set(catalog[slug]["role_inputs"])
    for prereq in group:
        kind = prereq["kind"]  # type: ignore[index]
        if kind == "role_present":
            if prereq["role"] not in active:  # type: ignore[index]
                return False
        elif kind == "input_present":
            if prereq["input"] not in (role_inputs | context_keys | visible_inputs):  # type: ignore[index]
                return False
        elif kind == "criteria_present":
            if prereq["criteria_key"] not in context_keys:  # type: ignore[index]
                return False
        elif kind == "registered_decision_present":
            if prereq["decision_key"] not in context_keys:  # type: ignore[index]
                return False
        elif kind == "profile_context_present":
            if prereq["profile"] not in profile_names:  # type: ignore[index]
                return False
        elif kind == "external_model_output_present":
            if prereq["role"] not in active:  # type: ignore[index]
                return False
        elif kind == "group_input_count":
            distinct = {e["source_identity"]["id"] for e in plan["context_registry"]["entries"]}  # type: ignore[assignment,index]
            if len(distinct) < prereq["minimum"]:  # type: ignore[index]
                return False
        else:
            return False
    return True


def _validate_final_authority(
    fa: Dict[str, object],
    plan: Dict[str, object],
    catalog: Dict[str, dict],
    tier: Dict[str, object],
    by_id: Dict[str, object],
) -> None:
    if fa["agent_id"] is None:  # type: ignore[index]
        if fa["action_refs"]:  # type: ignore[index]
            raise ValidationError("final_authority: null agent_id requires empty action_refs")
        if fa["decision_control"] != "human":  # type: ignore[index]
            raise ValidationError("final_authority: null agent_id requires decision_control 'human'")
        # Null authority => every terminal gate must be approval.
        for node in plan["interaction_graph"]["nodes"]:  # type: ignore[assignment]
            if node["kind"] == "human_gate" and _is_terminal(plan, node):  # type: ignore[arg-type]
                if node["mode"] != "approval":  # type: ignore[index]
                    raise ValidationError("final_authority null: terminal gate must be 'approval'")
        return

    holder_id = fa["agent_id"]  # type: ignore[index]
    holder = by_id.get(holder_id)
    if holder is None:
        raise ValidationError(f"final_authority: holder agent '{holder_id}' not found")

    if not tier["within_system_final_decision"]:  # type: ignore[index]
        raise ValidationError(
            f"final_authority: tier '{plan['domain_assessment']['tier']}' forbids within-system final decision"  # type: ignore[index]
        )

    selected = fa["decision_control"]  # type: ignore[index]
    if selected not in tier["decision_control_levels"]:  # type: ignore[index]
        raise ValidationError(f"final_authority: tier does not permit control '{selected}'")

    active_slugs = _active_role_slugs(holder)
    for ref in fa["action_refs"]:  # type: ignore[assignment]
        role_slug = ref["role_slug"]  # type: ignore[index]
        action_id = ref["action_id"]  # type: ignore[index]
        if role_slug not in active_slugs:
            raise ValidationError(f"final_authority: ref role '{role_slug}' not active in holder")
        spec = catalog[role_slug]
        action = next((a for a in spec["authority"]["actions"] if a["id"] == action_id), None)
        if action is None:
            raise ValidationError(f"final_authority: action '{action_id}' not declared by role '{role_slug}'")
        if action["scope"] != "internal":
            raise ValidationError(f"final_authority: external action ref '{action_id}' rejected")
        if not spec["authority"]["final_decision_eligible"]:
            raise ValidationError(f"final_authority: role '{role_slug}' is not final-decision eligible")
        if DECISION_RANK[selected] < DECISION_RANK[action["min_decision_control"]]:
            raise ValidationError(
                f"final_authority: control '{selected}' below action '{action_id}' minimum"
            )
        if selected not in set(spec["decision_control"]["allowed"]):
            raise ValidationError(f"final_authority: role '{role_slug}' does not allow control '{selected}'")

    if holder["resolved_design_settings"]["decision_control"] != selected:  # type: ignore[index]
        raise ValidationError("final_authority: holder resolved control not persisted as selected control")


def _validate_graph(plan: Dict[str, object], tier: Dict[str, object], catalog: Dict[str, dict]) -> None:
    graph = plan["interaction_graph"]  # type: ignore[assignment]
    nodes = graph["nodes"]  # type: ignore[assignment]

    node_by_id = {n["id"]: n for n in nodes}  # type: ignore[assignment,index]
    agent_nodes = [n for n in nodes if n["kind"] == "agent"]  # type: ignore[assignment]
    gate_nodes = [n for n in nodes if n["kind"] == "human_gate"]  # type: ignore[assignment]

    # Exactly one agent node per planned agent, role in portfolio.
    for agent in plan["agents"]:  # type: ignore[assignment]
        matching = [n for n in agent_nodes if n["agent_id"] == agent["id"]]  # type: ignore[index]
        if len(matching) != 1:
            raise ValidationError(f"graph: agent {agent['id']} must have exactly one agent node")  # type: ignore[index]
        node = matching[0]
        if node["role"] not in _active_role_slugs(agent):  # type: ignore[index]
            raise ValidationError(f"graph: node {node['id']} role not in agent portfolio")  # type: ignore[assignment]

    # Build canonical relation adjacency.
    adj: Dict[str, set] = {n["id"]: set() for n in nodes}  # type: ignore[assignment,index]
    for e in graph["edges"]:  # type: ignore[assignment]
        if e["from"] not in node_by_id or e["to"] not in node_by_id:  # type: ignore[assignment,index]
            raise ValidationError("graph: edge references unknown node")
        adj[e["from"]].add(e["to"])  # type: ignore[assignment,index]
    declared_outputs = {}
    for n in agent_nodes:
        declared_outputs[n["id"]] = set(n["declared_outputs"])  # type: ignore[assignment,index]
    for n in agent_nodes:
        for ref in n["visible_inputs"]:  # type: ignore[assignment]
            if ref["kind"] == "node_output" and ref["node_id"] in declared_outputs:  # type: ignore[assignment]
                if ref["output"] in declared_outputs[ref["node_id"]]:  # type: ignore[assignment]
                    adj[ref["node_id"]].add(n["id"])  # type: ignore[assignment]
    for agg in graph["aggregation"]:  # type: ignore[assignment]
        for ref in agg["inputs"]:  # type: ignore[assignment]
            if ref["kind"] == "node_output" and ref["node_id"] in node_by_id:  # type: ignore[assignment,index]
                adj[ref["node_id"]].add(agg["id"])  # type: ignore[assignment]
        if agg["destination_gate_id"] in node_by_id:  # type: ignore[assignment,index]
            adj[agg["id"]].add(agg["destination_gate_id"])  # type: ignore[assignment]

    # Acyclic (Kahn).
    indeg = {nid: 0 for nid in adj}
    for src, dsts in adj.items():
        for d in dsts:
            indeg[d] += 1
    from collections import deque

    queue = deque([nid for nid, d in indeg.items() if d == 0])
    visited = 0
    while queue:
        cur = queue.popleft()
        visited += 1
        for d in adj[cur]:
            indeg[d] -= 1
            if indeg[d] == 0:
                queue.append(d)
    if visited != len(adj):
        raise ValidationError("graph: cycle detected in canonical relation")

    # Phase strictly increases along every relation edge.
    phase = {n["id"]: n["phase"] for n in nodes}  # type: ignore[assignment,index]
    for src, dsts in adj.items():
        for d in dsts:
            if not (phase[src] < phase[d]):
                raise ValidationError(f"graph: phase does not increase from {src} to {d}")

    # Every node reachable from an agent node.
    reachable = set()
    for an in agent_nodes:
        stack = [an["id"]]
        while stack:
            cur = stack.pop()
            if cur in reachable:
                continue
            reachable.add(cur)
            stack.extend(adj[cur])
    if len(reachable) != len(nodes):
        raise ValidationError("graph: not all nodes reachable from an agent node")

    # At least one terminal gate; gate modes allowed by tier.
    terminals = [g for g in gate_nodes if _is_terminal(plan, g)]  # type: ignore[arg-type]
    if not terminals:
        raise ValidationError("graph: no terminal human gate present")
    for g in gate_nodes:
        if g["mode"] not in tier["terminal_gate_modes"]:  # type: ignore[assignment,index]
            raise ValidationError(f"graph: gate {g['id']} mode '{g['mode']}' not permitted by tier")  # type: ignore[assignment,index]

    _validate_trigger_evaluations(plan, catalog)


def _is_terminal(plan: Dict[str, object], gate: Dict[str, object]) -> bool:
    for e in plan["interaction_graph"]["edges"]:  # type: ignore[assignment]
        if e["from"] == gate["id"]:  # type: ignore[index]
            return False
    return True


def _validate_trigger_evaluations(plan: Dict[str, object], catalog: Dict[str, dict]) -> None:
    required: set = set()
    for agent in plan["agents"]:  # type: ignore[assignment]
        for slug in _active_role_slugs(agent):
            spec = catalog[slug]
            required |= set(spec["agreement_disagreement"]["required_triggers"])
    evaluations = {t["trigger_id"]: t for t in plan["trigger_evaluations"]}  # type: ignore[assignment,index]
    for trig in required:
        if trig not in evaluations:
            raise ValidationError(f"trigger: required trigger '{trig}' has no evaluation")
    for trig_id, ev in evaluations.items():
        if trig_id not in required:
            raise ValidationError(f"trigger: evaluation '{trig_id}' is not a required trigger")
        for ref in ev["evidence_refs"]:  # type: ignore[assignment]
            _resolve_evidence_ref(ref, plan)


def _resolve_evidence_ref(ref: Dict[str, object], plan: Dict[str, object]) -> None:
    kind = ref["kind"]  # type: ignore[index]
    if kind == "context":
        keys = {e["key"] for e in plan["context_registry"]["entries"]}  # type: ignore[assignment,index]
        if ref["key"] not in keys:  # type: ignore[index]
            raise ValidationError(f"evidence_ref: context key {ref['key']} unresolved")  # type: ignore[index]
    elif kind == "profile":
        ids = {e["id"] for e in plan["profile_evidence_registry"]["entries"]}  # type: ignore[assignment,index]
        if ref["evidence_id"] not in ids:  # type: ignore[index]
            raise ValidationError(f"evidence_ref: profile id {ref['evidence_id']} unresolved")  # type: ignore[index]
    elif kind == "domain_assessment":
        if ref["index"] >= len(plan["domain_assessment"]["evidence"]):  # type: ignore[index]
            raise ValidationError("evidence_ref: domain_assessment index out of range")
    elif kind == "node_output":
        node = next((n for n in plan["interaction_graph"]["nodes"] if n["id"] == ref["node_id"]), None)  # type: ignore[assignment]
        if node is None:
            raise ValidationError(f"evidence_ref: node {ref['node_id']} unresolved")  # type: ignore[index]
        if ref["output"] not in node["declared_outputs"]:  # type: ignore[index]
            raise ValidationError(f"evidence_ref: output {ref['output']} not declared by node")  # type: ignore[index]
    else:
        raise ValidationError(f"evidence_ref: unknown kind {kind}")


__all__ = [
    "CATALOG_SLUGS",
    "SCHEMA_VERSION",
    "DECISION_CONTROL",
    "SCOPE",
    "ORIENTATIONS",
    "COGNITIVE_MODES",
    "SOCIAL_POSITIONS",
    "AGREEMENT_MODES",
    "KNOWLEDGE_MODES",
    "GATE_MODES",
    "PROFILE_NAMES",
    "IMPACT_TIERS",
    "TRIGGER_IDS",
    "ValidationError",
    "as_id",
    "as_text",
    "as_markdown",
    "as_path",
    "as_sha256",
    "as_nonnegative_int",
    "as_boolean",
    "as_decision_control",
    "as_scope",
    "as_generated_at",
    "as_role_slug",
    "as_enum",
    "parse_closed_object",
    "as_unique_list",
    "parse_source_identity",
    "parse_context_entry",
    "parse_provenance_source",
    "parse_provenance_policy",
    "parse_human_source",
    "parse_human_source_registry",
    "parse_stakeholder_source_ref",
    "parse_stakeholder",
    "parse_stakeholder_registry",
    "parse_profile_evidence",
    "parse_profile_evidence_registry",
    "parse_synthetic_perspective",
    "parse_synthetic_perspective_registry",
    "parse_role_assignment",
    "parse_calibration",
    "parse_profile_rationale",
    "parse_claim_source_ref",
    "parse_claim_provenance",
    "parse_resolved_settings",
    "parse_action_ref",
    "parse_candidate_agent",
    "parse_planned_agent",
    "parse_hash_ref",
    "parse_generation_provenance",
    "parse_domain_assessment",
    "parse_final_authority",
    "parse_trigger_evaluation",
    "parse_evidence_ref",
    "parse_typed_input_ref",
    "parse_interaction_graph",
    "parse_interaction_posture_snapshot",
    "parse_projection_hashes",
    "parse_context_registry",
    "parse_candidate_agent_plan",
    "parse_agent_plan",
    "validate_candidate_plan",
    "validate_agent_plan",
    "DEFAULT_DOMAIN_POLICY",
    "parse_domain_policy",
    "load_domain_policy",
    "DECISION_RANK",
    "sha256_text",
    "derive_social_positions",
    "recompute_resolved_settings",
    "derive_role_scoped_authority",
    "enrich_candidate_to_planned",
    "compute_projection_hashes",
    "validate_agent_plan_semantics",
]
