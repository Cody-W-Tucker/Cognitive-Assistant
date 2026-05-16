#!/usr/bin/env python3
"""Helpers for reading crystallization artifacts and rendering rule overlays."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import Config


ARTIFACT_FILENAME = "crystallization.json"
RULES_FILENAME = "adaptation_rules.md"
SKILL_ADAPTATIONS_FILENAME = "skill_adaptations.json"
MIN_PRECISION_WEIGHT = 0.75


def utc_now_iso() -> str:
    """Return a stable UTC timestamp for artifact bookkeeping."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def artifact_path_for_config(config: Config) -> Path:
    """Return the canonical crystallization artifact path for a profile."""
    return config.paths.DATA_DIR / ARTIFACT_FILENAME


def rules_path_for_config(config: Config) -> Path:
    """Return the derived adaptation rules path for a profile."""
    return config.paths.ARTIFACTS_DIR / RULES_FILENAME


def skill_adaptations_path_for_config(config: Config) -> Path:
    """Return the derived machine-consumable skill adaptations path."""
    return config.paths.ARTIFACTS_DIR / SKILL_ADAPTATIONS_FILENAME


def load_artifact(path: Path) -> Dict[str, Any]:
    """Load a crystallization artifact if it exists, else return an empty shell."""
    if not path.exists():
        return {
            "version": 1,
            "profile": None,
            "updated_at": None,
            "adaptations": [],
        }

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Crystallization artifact must be a JSON object: {path}")

    adaptations = payload.get("adaptations", [])
    if not isinstance(adaptations, list):
        raise ValueError("Crystallization artifact field 'adaptations' must be a list")
    payload["adaptations"] = adaptations
    return payload


def write_artifact(path: Path, artifact: Dict[str, Any]) -> Path:
    """Write the crystallization artifact to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def normalize_input_payload(payload: Any) -> List[Dict[str, Any]]:
    """Accept either a raw list of adaptations or an object with an adaptations list."""
    if isinstance(payload, dict):
        payload = payload.get("adaptations", [])

    if not isinstance(payload, list):
        raise ValueError("Input payload must be a list or an object with an 'adaptations' list")

    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Adaptation #{index} must be a JSON object")
        normalized.append(dict(item))
    return normalized


def merge_adaptations(
    existing_adaptations: List[Dict[str, Any]],
    incoming_adaptations: List[Dict[str, Any]],
    *,
    profile: str,
) -> List[Dict[str, Any]]:
    """Merge incoming Hermes-produced adaptations into managed artifact state."""
    now = utc_now_iso()
    existing_by_id = {
        str(item.get("id")): dict(item)
        for item in existing_adaptations
        if isinstance(item, dict) and item.get("id")
    }

    merged_order: List[str] = []
    merged_by_id: Dict[str, Dict[str, Any]] = {}

    for incoming in incoming_adaptations:
        adaptation_id = str(incoming.get("id") or "").strip()
        if not adaptation_id:
            raise ValueError("Each adaptation must include a non-empty 'id'")

        existing = existing_by_id.get(adaptation_id, {})
        times_seen = int(existing.get("times_seen", 0)) + 1
        merged = dict(existing)
        merged.update(incoming)
        merged["id"] = adaptation_id
        merged["profile"] = profile
        merged["first_seen"] = existing.get("first_seen", now)
        merged["last_seen"] = now
        merged["times_seen"] = times_seen
        merged["precision_weight"] = float(merged.get("precision_weight", 0.0))
        merged["status"] = str(merged.get("status", "confirmed"))
        merged["captured_upstream"] = bool(merged.get("captured_upstream", False))
        merged.setdefault("captured_in", None)
        merged.setdefault("captured_at", None)
        merged.setdefault("notes", None)

        if adaptation_id in existing_by_id and existing.get("captured_upstream"):
            merged["captured_upstream"] = False
            merged["captured_in"] = None
            merged["captured_at"] = None
            merged["status"] = "confirmed"
            merged["recurred_after_capture"] = True

        merged_by_id[adaptation_id] = merged
        merged_order.append(adaptation_id)

    for existing in existing_adaptations:
        if not isinstance(existing, dict):
            continue
        adaptation_id = existing.get("id")
        if not adaptation_id or adaptation_id in merged_by_id:
            continue
        merged_by_id[str(adaptation_id)] = dict(existing)
        merged_order.append(str(adaptation_id))

    deduped_order: List[str] = []
    seen: set[str] = set()
    for adaptation_id in merged_order:
        if adaptation_id in seen:
            continue
        seen.add(adaptation_id)
        deduped_order.append(adaptation_id)

    return [merged_by_id[adaptation_id] for adaptation_id in deduped_order]


def active_adaptations(config: Config) -> List[Dict[str, Any]]:
    """Return high-signal adaptations that should shape current generation runs."""
    artifact = load_artifact(artifact_path_for_config(config))
    active: List[Dict[str, Any]] = []
    for item in artifact.get("adaptations", []):
        if not isinstance(item, dict):
            continue
        if item.get("status") == "retired":
            continue
        try:
            precision = float(item.get("precision_weight", 0.0))
        except (TypeError, ValueError):
            continue
        if precision < MIN_PRECISION_WEIGHT:
            continue
        active.append(item)
    return active


def render_rule_overlay(adaptations: List[Dict[str, Any]]) -> str:
    """Render active adaptations as a compact prompt overlay."""
    if not adaptations:
        return ""

    lines = [
        "<adaptation_rules>",
        "These confirmed adaptations are high-signal corrections from runtime use.",
        "Treat them as constraints to preserve in the generated output when relevant.",
        "",
    ]
    for adaptation in adaptations:
        proposed = adaptation.get("proposed_update")
        if isinstance(proposed, dict):
            proposed_text = json.dumps(proposed, ensure_ascii=True, sort_keys=True)
        else:
            proposed_text = str(proposed or "")
        lines.extend(
            [
                f"- id: {adaptation.get('id')}",
                f"  type: {adaptation.get('type', 'unknown')}",
                f"  source: {adaptation.get('source', 'unknown')}",
                f"  observed_need: {adaptation.get('observed_need') or adaptation.get('actual_behavior') or 'n/a'}",
                f"  proposed_update: {proposed_text}",
                f"  precision_weight: {adaptation.get('precision_weight')}",
            ]
        )
    lines.append("</adaptation_rules>")
    return "\n".join(lines)


def write_rules_overlay(config: Config, adaptations: List[Dict[str, Any]]) -> Optional[Path]:
    """Persist the derived adaptation rules for inspection by operators."""
    overlay = render_rule_overlay(adaptations)
    out_path = rules_path_for_config(config)
    if not overlay:
        if out_path.exists():
            out_path.unlink()
        return None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(overlay + "\n", encoding="utf-8")
    return out_path


def build_skill_adaptations(
    config: Config, adaptations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Project active crystallizations into a downstream composition format."""
    skill_payload: Dict[str, Dict[str, List[str]]] = {}
    global_prepend: List[str] = []

    for adaptation in adaptations:
        if not isinstance(adaptation, dict):
            continue
        proposed = adaptation.get("proposed_update")
        if not isinstance(proposed, dict):
            continue

        content = str(proposed.get("content") or proposed.get("value") or "").strip()
        if not content:
            continue

        target = str(proposed.get("target") or "").strip()
        action = str(proposed.get("action") or "prepend").strip()
        if action not in {"prepend", "append"}:
            continue

        if target in {"global_skill_preamble", "skills_global", "global"}:
            if action == "prepend" and content not in global_prepend:
                global_prepend.append(content)
            continue

        if target not in {"skill", "skills", "tool_specs", "tool_spec"}:
            continue

        skill_name = str(
            proposed.get("skill") or proposed.get("tool") or proposed.get("name") or ""
        ).strip()
        if not skill_name:
            continue

        entry = skill_payload.setdefault(skill_name, {"prepend": [], "append": []})
        if content not in entry[action]:
            entry[action].append(content)

    return {
        "version": 1,
        "profile": config.profile.name,
        "updated_at": utc_now_iso(),
        "global": {
            "prepend": global_prepend,
        },
        "skills": dict(sorted(skill_payload.items())),
    }


def write_skill_adaptations(config: Config, adaptations: List[Dict[str, Any]]) -> Path:
    """Write the machine-consumable skill adaptation projection."""
    out_path = skill_adaptations_path_for_config(config)
    payload = build_skill_adaptations(config, adaptations)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path


def mark_adaptations_captured(
    config: Config,
    adaptation_ids: List[str],
    *,
    captured_in: str,
) -> Optional[Path]:
    """Mark active adaptations as absorbed by a successful CA generation run."""
    if not adaptation_ids:
        return None

    artifact_path = artifact_path_for_config(config)
    artifact = load_artifact(artifact_path)
    now = utc_now_iso()
    id_set = set(adaptation_ids)
    changed = False

    for item in artifact.get("adaptations", []):
        if not isinstance(item, dict):
            continue
        if str(item.get("id")) not in id_set:
            continue
        item["captured_upstream"] = True
        item["captured_in"] = captured_in
        item["captured_at"] = now
        if item.get("status") != "retired":
            item["status"] = "applied"
        changed = True

    if not changed:
        return None

    artifact["updated_at"] = now
    artifact["summary"] = summarize_artifact(artifact.get("adaptations", []))
    return write_artifact(artifact_path, artifact)


def summarize_artifact(adaptations: List[Dict[str, Any]]) -> Dict[str, int]:
    """Summarize adaptation counts by status for quick inspection."""
    summary: Dict[str, int] = {
        "total": 0,
        "active": 0,
        "captured_upstream": 0,
    }
    for item in adaptations:
        if not isinstance(item, dict):
            continue
        summary["total"] += 1
        if item.get("status") != "retired":
            summary["active"] += 1
        if item.get("captured_upstream"):
            summary["captured_upstream"] += 1
    return summary


__all__ = [
    "ARTIFACT_FILENAME",
    "MIN_PRECISION_WEIGHT",
    "SKILL_ADAPTATIONS_FILENAME",
    "active_adaptations",
    "artifact_path_for_config",
    "build_skill_adaptations",
    "load_artifact",
    "mark_adaptations_captured",
    "merge_adaptations",
    "normalize_input_payload",
    "render_rule_overlay",
    "rules_path_for_config",
    "skill_adaptations_path_for_config",
    "summarize_artifact",
    "utc_now_iso",
    "write_artifact",
    "write_rules_overlay",
    "write_skill_adaptations",
]
