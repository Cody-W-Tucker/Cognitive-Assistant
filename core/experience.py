#!/usr/bin/env python3
"""Accepted change records: the lineage the living SOUL is built from.

    <ca_home>/experience/authored/<id>.md   one accepted record (front matter + markdown)
    <ca_home>/experience/reverted.jsonl     records withdrawn after adoption

``core.improve.apply`` writes records and ``core.improve.auto_cycle`` withdraws
them; the living SOUL reads the active ones and a rebootstrap reads them all.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

from core.paths import atomic_write, experience_dir

RECORD_FIELDS = (
    "id",
    "title",
    "body",
    "sources",
    "clusterId",
    "evidence",
    "counterevidence",
    "compilerImplication",
)


def is_complete(record: Dict) -> bool:
    """Whether a record carries every field an accepted record needs."""
    return all(record.get(field) for field in RECORD_FIELDS)


def _authored_dir() -> Path:
    return experience_dir() / "authored"


def _reverted_path() -> Path:
    return experience_dir() / "reverted.jsonl"


def record_path(record_id: str) -> Path:
    return _authored_dir() / f"{record_id}.md"


def render(record: Dict, edit: Dict, proposal_id: str) -> str:
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "---",
        f"id: {record['id']}",
        f"title: {record['title']}",
        f"sources: {', '.join(record['sources'])}",
        f"cluster: {record['clusterId']}",
        f"proposal: {proposal_id}",
        f"created: {created}",
        "---",
        "",
        f"# {record['title']}",
        "",
        record["body"],
        "",
        "## Evidence",
        "",
    ]
    lines.extend(f"- ({item.get('source', 'unknown')}) {item.get('text', '')}" for item in record["evidence"])
    lines.extend(
        [
            "",
            "## Counterevidence",
            "",
            str(record["counterevidence"]),
            "",
            "## Compiler implication",
            "",
            str(record["compilerImplication"]),
            "",
            f"_Accepted from {edit.get('id', '?')} ({edit.get('kind', '?')}); rationale: {edit.get('rationale', '')}_",
            "",
        ]
    )
    return "\n".join(lines)


def parse(text: str) -> Dict[str, str]:
    """Front matter fields, title, and the instruction body (text before the first ``##``)."""
    meta: Dict[str, str] = {}
    rest = text
    if text.startswith("---\n"):
        header, _, rest = text[4:].partition("\n---\n")
        for line in header.splitlines():
            key, sep, value = line.partition(":")
            if sep:
                meta[key.strip()] = value.strip()
    title = meta.get("title", "")
    body_lines: List[str] = []
    seen_heading = False
    for line in rest.splitlines():
        if not seen_heading:
            if line.startswith("# "):
                title = title or line[2:].strip()
                seen_heading = True
            continue
        if line.startswith("## "):
            break
        body_lines.append(line)
    return {**meta, "title": title, "instruction": "\n".join(body_lines).strip()}


def write(record: Dict, edit: Dict, proposal_id: str) -> Path:
    path = record_path(record["id"])
    atomic_write(path, render(record, edit, proposal_id))
    return path


def _stored() -> List[tuple[str, str]]:
    """(record id, file text) for every accepted record, in file order."""
    directory = _authored_dir()
    if not directory.is_dir():
        return []
    out = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        out.append((parse(text).get("id") or path.stem, text))
    return out


def read(record_id: str) -> Dict[str, str]:
    """One stored record's front matter, title and instruction."""
    return {**parse(record_path(record_id).read_text(encoding="utf-8")), "id": record_id}


def reverted_ids() -> Set[str]:
    """Record ids withdrawn after adoption (kept in lineage as negative evidence)."""
    path = _reverted_path()
    ids: Set[str] = set()
    if not path.exists():
        return ids
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            ids.add(str(json.loads(line)["record"]))
        except (ValueError, KeyError, TypeError):
            continue
    return ids


def withdraw(record_ids: List[str], reason: str) -> None:
    path = _reverted_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(path, "a", encoding="utf-8") as handle:
        for record_id in record_ids:
            handle.write(json.dumps({"at": at, "record": record_id, "reason": reason}, sort_keys=True) + "\n")


def active(exclude: Set[str]) -> List[Dict[str, str]]:
    """Accepted, not withdrawn, not in ``exclude``, with an instruction; oldest first."""
    skip = exclude | reverted_ids()
    records = []
    for record_id, text in _stored():
        record = {**parse(text), "id": record_id}
        if record_id in skip or not record["instruction"]:
            continue
        records.append(record)
    records.sort(key=lambda record: (record.get("created", ""), record["id"]))
    return records


def lineage() -> Dict:
    """Every record ever adopted or withdrawn, for a rebootstrap from source data.

    A rebootstrap does not inherit the previous SOUL, so it sees all accepted
    records (including ones an earlier bootstrap absorbed) with their evidence,
    plus withdrawn records as changes that were tried and reverted.
    """
    withdrawn = reverted_ids()
    adopted: List[str] = []
    withdrawn_blocks: List[str] = []
    adopted_blocks: List[str] = []
    for record_id, text in _stored():
        status = "withdrawn" if record_id in withdrawn else "adopted"
        block = f'<record id="{record_id}" status="{status}">\n{text.strip()}\n</record>'
        if status == "adopted":
            adopted.append(record_id)
            adopted_blocks.append(block)
        else:
            withdrawn_blocks.append(block)
    if not adopted_blocks and not withdrawn_blocks:
        return {"text": "(no lineage: nothing has been adopted in use yet)", "records": []}
    return {"text": "\n\n".join(adopted_blocks + withdrawn_blocks), "records": adopted}
