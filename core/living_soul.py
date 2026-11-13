#!/usr/bin/env python3
"""Living SOUL: a deterministic runtime build of bootstrap SOUL + lineage.

The repo produces the *bootstrap* SOUL from source data. At runtime CA home
owns everything that changes afterwards:

    <ca_home>/soul/compose.json             wrapper text paths set by the deployer
    <ca_home>/soul/generations/NNNN.md      every compiled SOUL, never edited
    <ca_home>/soul/generations/NNNN.json    its inputs (bootstrap sha, record ids)
    <ca_home>/soul/current.md               symlink to the active generation
    <ca_home>/soul/activations.jsonl        when each generation became active

A generation is a pure function of (wrapper, bootstrap SOUL, active records).
It never reads the previous generation, so a change cannot compound on its own
output, and rollback is repointing ``current.md``. Records a bootstrap already
absorbed (listed in ``absorbed.json`` beside the bootstrap SOUL) are left out,
so a rebootstrap that folded them into the SOUL does not count them twice.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from core import experience, journal, paths
from core.paths import atomic_write, soul_dir

ABSORBED_FILENAME = "absorbed.json"
LEARNED_HEADING = "## Learned in use"


def generations_dir() -> Path:
    return soul_dir() / "generations"


def current_path() -> Path:
    return soul_dir() / "current.md"


def running_soul_path() -> Path:
    """The SOUL Hermes is running: the living SOUL once compiled, else the bootstrap."""
    current = current_path()
    return current if current.exists() else paths.BOOTSTRAP_SOUL_PATH


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def absorbed_ids(bootstrap: Path) -> Set[str]:
    """Record ids the bootstrap SOUL already took into account."""
    path = bootstrap.parent / ABSORBED_FILENAME
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(record_id) for record_id in data.get("records", [])}


def write_absorbed(bootstrap: Path, record_ids: List[str]) -> Path:
    """Declare which lineage records this bootstrap took into account."""
    path = bootstrap.parent / ABSORBED_FILENAME
    payload = {
        "records": sorted(record_ids),
        "note": "Lineage records this bootstrap SOUL was built with; the living SOUL leaves them out.",
    }
    atomic_write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _compose_config_path() -> Path:
    return soul_dir() / "compose.json"


def read_compose_config() -> Dict[str, Optional[str]]:
    path = _compose_config_path()
    if not path.exists():
        return {"prefix": None, "suffix": None}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"prefix": data.get("prefix"), "suffix": data.get("suffix")}


def write_compose_config(prefix: Optional[str], suffix: Optional[str]) -> Path:
    """Record the deployer's wrapper files so every later compile uses the same ones."""
    path = _compose_config_path()
    atomic_write(path, json.dumps({"prefix": prefix, "suffix": suffix}, indent=2, sort_keys=True) + "\n")
    return path


def _read_optional(path: Optional[str]) -> str:
    return Path(path).read_text(encoding="utf-8").strip() if path else ""


def compose(bootstrap_text: str, records: List[Dict[str, str]], prefix: str = "", suffix: str = "") -> str:
    parts = [prefix] if prefix else []
    parts.append(bootstrap_text.strip())
    if records:
        learned = [
            LEARNED_HEADING,
            "",
            "Adopted from observed sessions after this SOUL was bootstrapped. Each is"
            " conditional on the situation it names.",
        ]
        for record in records:
            learned.extend(["", f"### {record['title'] or record['id']}", "", record["instruction"]])
        parts.append("\n".join(learned))
    if suffix:
        parts.append(suffix)
    return "\n\n".join(parts) + "\n"


def activations() -> List[Dict]:
    """Ordered (at, generation) history of which generation Hermes was running."""
    path = soul_dir() / "activations.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def _point_current(generation_file: Path) -> None:
    number = int(generation_file.stem)
    previous = current_generation()
    link = current_path()
    tmp = link.with_name(f".current-{os.getpid()}")
    tmp.unlink(missing_ok=True)
    os.symlink(os.path.relpath(generation_file, link.parent), tmp)
    os.replace(tmp, link)
    if not previous or previous.get("generation") != number:
        row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "generation": number}
        with open(soul_dir() / "activations.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def list_generations() -> List[Dict]:
    directory = generations_dir()
    if not directory.is_dir():
        return []
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(directory.glob("*.json"))]


def current_generation() -> Optional[Dict]:
    link = current_path()
    if not link.is_symlink():
        return None
    meta = link.resolve().with_suffix(".json")
    return json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else None


def compile_soul(*, reason: str = "compile") -> Dict:
    """Build the living SOUL from its inputs; new generation only when the output changes."""
    bootstrap = paths.BOOTSTRAP_SOUL_PATH
    bootstrap_text = bootstrap.read_text(encoding="utf-8")
    if not bootstrap_text.strip():
        raise RuntimeError(f"bootstrap SOUL is empty: {bootstrap}")
    records = experience.active(exclude=absorbed_ids(bootstrap))
    config = read_compose_config()
    text = compose(
        bootstrap_text,
        records,
        prefix=_read_optional(config["prefix"]),
        suffix=_read_optional(config["suffix"]),
    )
    sha = _sha256(text)
    current = current_generation()
    if current and current.get("sha256") == sha:
        _point_current(generations_dir() / f"{current['generation']:04d}.md")
        return {**current, "changed": False}
    number = max((g["generation"] for g in list_generations()), default=0) + 1
    record_ids = [record["id"] for record in records]
    previous_ids = (current or {}).get("records", [])
    bootstrap_sha = _sha256(bootstrap_text)
    meta = {
        "generation": number,
        "sha256": sha,
        "bootstrapSha256": bootstrap_sha,
        "records": record_ids,
        "createdAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reason": reason,
        # What changed relative to the generation it replaces; the outcome
        # check attributes a regression to exactly these records.
        "parent": current["generation"] if current else None,
        "added": [r for r in record_ids if r not in previous_ids],
        "removed": [r for r in previous_ids if r not in record_ids],
        "bootstrapChanged": bool(current) and current.get("bootstrapSha256") != bootstrap_sha,
    }
    generation_file = generations_dir() / f"{number:04d}.md"
    atomic_write(generation_file, text)
    atomic_write(generation_file.with_suffix(".json"), json.dumps(meta, indent=2, sort_keys=True) + "\n")
    _point_current(generation_file)
    journal.record(
        "soul_compiled",
        {
            "generation": number,
            "output_ref": sha,
            "bootstrap_ref": bootstrap_sha,
            "record_ids": record_ids,
            "reason": reason[:80],
        },
    )
    return {**meta, "changed": True}


def rollback(generation: int) -> Dict:
    """Repoint current.md at an earlier generation without recompiling."""
    target = generations_dir() / f"{generation:04d}.md"
    if not target.exists():
        raise RuntimeError(f"no generation {generation} under {generations_dir()}")
    _point_current(target)
    meta = json.loads(target.with_suffix(".json").read_text(encoding="utf-8"))
    journal.record("soul_rolled_back", {"generation": generation, "output_ref": meta["sha256"]})
    return meta


def revert_records(record_ids: List[str], reason: str) -> Dict:
    """Withdraw adopted records (kept in lineage) and compile without them."""
    experience.withdraw(record_ids, reason)
    return compile_soul(reason=f"revert {', '.join(record_ids)}"[:80])


def link_into(hermes_home: Path) -> Path:
    """Make ``<hermes_home>/SOUL.md`` a symlink to the living SOUL."""
    link = Path(hermes_home) / "SOUL.md"
    link.parent.mkdir(parents=True, exist_ok=True)
    tmp = link.with_name(f".SOUL.md-{os.getpid()}")
    tmp.unlink(missing_ok=True)
    os.symlink(current_path(), tmp)
    os.replace(tmp, link)
    return link
