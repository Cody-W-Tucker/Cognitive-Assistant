#!/usr/bin/env python3
"""Durable experience records for the CA improvement runtime.

Two layouts, mirroring the compiler's authored/generated split:

- ``authored/`` -- human/gate-approved record sources (durable, hand-editable).
- ``staged/`` -- generated artifacts compiled from an accepted record plus the
  read-only SOUL baseline (regenerable, never hand-edited).

The apply gate (``core.improve.apply``) is the sole writer. The experience
compiler (``compile_experience_block``) is the only consumer downstream.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]


def experience_root(repo_root: Path = REPO_ROOT) -> Path:
    """Return the experience store root (defaults to workspaces/experience)."""
    return repo_root / "workspaces" / "experience"


def authored_dir(root: Optional[Path] = None) -> Path:
    """Return the authored-sources directory."""
    return (root or experience_root()) / "authored"


def staged_dir(root: Optional[Path] = None) -> Path:
    """Return the staged-artifacts directory."""
    return (root or experience_root()) / "staged"


def render_authored_source(record: Dict, edit: Dict, proposal_id: str) -> str:
    """Render the durable authored source for an accepted record."""
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sources = ", ".join(record.get("sources", []))
    lines = [
        "---",
        f"id: {record['id']}",
        f"title: {record.get('title', '')}",
        f"sources: {sources}",
        f"proposal: {proposal_id}",
        f"created: {created}",
        "---",
        "",
        f"# {record.get('title', record['id'])}",
        "",
        record.get("body", ""),
        "",
        "## Evidence",
        "",
    ]
    for item in record.get("evidence", []):
        lines.append(f"- ({item.get('source', 'unknown')}) {item.get('text', '')}")
    lines.append("")
    lines.append(f"_Accepted from {edit.get('id', '?')} ({edit.get('kind', '?')}); rationale: {edit.get('rationale', '')}_")
    lines.append("")
    return "\n".join(lines)


def _atomic_write(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically (tmp file + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def write_authored_source(root: Path, record: Dict, edit: Dict, proposal_id: str) -> Path:
    """Atomically write the authored source; return its path."""
    path = authored_dir(root) / f"{record['id']}.md"
    _atomic_write(path, render_authored_source(record, edit, proposal_id))
    return path


def write_staged_artifact(root: Path, record_id: str, staged_text: str) -> Path:
    """Atomically write the staged generated artifact; return its path."""
    path = staged_dir(root) / f"{record_id}.md"
    _atomic_write(path, staged_text)
    return path


def iter_authored_sources(root: Optional[Path] = None) -> List[Path]:
    """Return sorted authored-source paths (empty when the store is absent)."""
    directory = authored_dir(root)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.md"))


def iter_staged_artifacts(root: Optional[Path] = None) -> List[Path]:
    """Return sorted staged-artifact paths (empty when the store is absent)."""
    directory = staged_dir(root)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.md"))


def compile_experience_block(
    root: Optional[Path] = None,
    *,
    max_chars: int = 6000,
) -> str:
    """Compile durable authored sources + staged artifacts into one block.

    This is the experience compiler hook consumed by downstream builds: it
    concatenates accepted authored sources with their staged artifacts. The
    SOUL baseline is never an input here -- callers pass SOUL separately and
    it stays the read-only baseline. Returns "" when the store is empty.
    """
    chunks: List[str] = []
    staged_by_id = {}
    for staged_path in iter_staged_artifacts(root):
        try:
            staged_by_id[staged_path.stem] = staged_path.read_text(encoding="utf-8")
        except OSError:
            continue
    authored_by_id = {}
    for source_path in iter_authored_sources(root):
        try:
            authored_by_id[source_path.stem] = source_path.read_text(encoding="utf-8")
        except OSError:
            continue
    for record_id in sorted(set(authored_by_id) | set(staged_by_id)):
        if record_id in authored_by_id:
            chunks.append(f"## Experience record: {record_id}\n\n{authored_by_id[record_id]}")
            if sum(len(c) for c in chunks) >= max_chars:
                break
        if record_id in staged_by_id:
            chunks.append(f"## Staged experience: {record_id}\n\n{staged_by_id[record_id]}")
            if sum(len(c) for c in chunks) >= max_chars:
                break
    block = "\n\n---\n\n".join(chunks)
    return block[:max_chars]
