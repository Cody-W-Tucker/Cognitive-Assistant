#!/usr/bin/env python3
"""Where the CA keeps things.

The checkout (or package) carries the bootstrap artifacts: skills under
``workspaces/skills/<group>/<slug>/SKILL.md`` and the alignment layer (SOUL,
interaction posture, alignment spec). Per-profile paths live on
``core.config.LayerProfile``. Everything that
changes at runtime lives under CA home, which ``$CA_HOME`` overrides:

    <ca_home>/improve/      improvement-pass state (evidence, ledger, proposal, journal)
    <ca_home>/experience/   accepted change records (lineage)
    <ca_home>/soul/         living SOUL generations
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "workspaces" / "skills"
ALIGNMENT_PROMPTS_DIR = REPO_ROOT / "profiles" / "alignment" / "prompts"
ALIGNMENT_ARTIFACTS_DIR = REPO_ROOT / "workspaces" / "alignment" / "artifacts"
BOOTSTRAP_SOUL_PATH = ALIGNMENT_ARTIFACTS_DIR / "SOUL.md"
INTERACTION_POSTURE_PATH = ALIGNMENT_ARTIFACTS_DIR / "INTERACTION_POSTURE.md"
ALIGNMENT_SPEC_PATH = ALIGNMENT_ARTIFACTS_DIR / "alignment_spec.md"


def ca_home() -> Path:
    """Root of all CA runtime state (``$CA_HOME`` or the XDG data dir)."""
    override = os.environ.get("CA_HOME")
    if override:
        return Path(override).expanduser()
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "cognitive-assistant"


def improve_dir() -> Path:
    return ca_home() / "improve"


def experience_dir() -> Path:
    return ca_home() / "experience"


def soul_dir() -> Path:
    return ca_home() / "soul"


def atomic_write(path: Path, content: str) -> None:
    """Replace ``path`` with ``content`` so readers never see a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def utc_now() -> str:
    """Current UTC time as ISO-8601 to the second."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_jsonl(path: Path, rows: Iterable[Dict], *, sort_keys: bool = True) -> None:
    """Append one JSON line per row to ``path``, creating its directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=sort_keys) + "\n")


def read_jsonl(path: Path) -> List[Any]:
    """Parsed lines of ``path``, skipping unparseable ones; [] when it is missing."""
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows
