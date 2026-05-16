#!/usr/bin/env python3
"""Manage the crystallization artifact that Hermes produces for CA to consume."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import adaptation_rules
from core.config import get_profile


def detect_adaptations(profile: str) -> List[Dict[str, Any]]:
    """Return stub data for local development when Hermes input is unavailable."""
    return [
        {
            "id": "adapt-001",
            "type": "skill_override",
            "source": "gws-drive skill patch",
            "original_model": "use gws-drive for all Drive access without local fallback",
            "observed_need": "Hermes had to fall back to direct file read on /nix/store paths",
            "precision_weight": 0.92,
            "status": "confirmed",
            "proposed_update": {
                "target": "skill",
                "skill": "gws-drive",
                "action": "prepend",
                "content": "Preserve explicit guidance for read-only /nix/store fallback handling.",
            },
        }
    ]


def read_input_payload(input_path: Optional[Path]) -> List[Dict[str, Any]]:
    """Load Hermes-provided adaptations from JSON, if supplied."""
    if input_path is None:
        return []

    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    return adaptation_rules.normalize_input_payload(payload)


def write_artifact(
    profile: str,
    adaptations: List[Dict[str, Any]],
    *,
    out_path: Path,
) -> Path:
    """Write or update the managed crystallization artifact."""
    existing = adaptation_rules.load_artifact(out_path)
    merged_adaptations = adaptation_rules.merge_adaptations(
        existing.get("adaptations", []), adaptations, profile=profile
    )
    artifact = {
        "version": 1,
        "profile": profile,
        "updated_at": adaptation_rules.utc_now_iso(),
        "adaptations": merged_adaptations,
        "summary": adaptation_rules.summarize_artifact(merged_adaptations),
    }
    return adaptation_rules.write_artifact(out_path, artifact)


def default_output_path(profile: str) -> Path:
    """Resolve the default artifact path for repo-local runs."""
    cfg = get_profile(profile)
    out_path = cfg.workspace_dir / "data" / adaptation_rules.ARTIFACT_FILENAME
    if str(out_path).startswith("/nix/store/"):
        raise ValueError(
            "Default crystallization output resolves inside /nix/store. "
            "Pass --output when invoking the flake-exported package."
        )
    return out_path


def crystallize(
    profile: str = "operational",
    *,
    output_path: Optional[Path] = None,
    input_path: Optional[Path] = None,
) -> Path:
    """Main entry point for the crystallization pass."""
    print(f"Running crystallization for profile: {profile}")

    raw = read_input_payload(input_path) if input_path else detect_adaptations(profile)
    out_path = Path(output_path) if output_path is not None else default_output_path(profile)
    written_path = write_artifact(profile, raw, out_path=out_path)

    print(f"Crystallization artifact written: {written_path}")
    return written_path


def run(
    profile: str = "operational",
    *,
    output_path: Optional[Path] = None,
    input_path: Optional[Path] = None,
) -> int:
    """CLI-friendly entry point."""
    try:
        crystallize(profile, output_path=output_path, input_path=input_path)
    except Exception as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="operational")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    raise SystemExit(
        run(profile=args.profile, output_path=args.output, input_path=args.input)
    )
