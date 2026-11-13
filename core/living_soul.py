#!/usr/bin/env python3
"""Living SOUL: a deterministic runtime build of bootstrap SOUL + lineage.

The repo produces the *bootstrap* SOUL from source data. At runtime the CA
state dir owns everything that changes afterwards:

    <ca_home>/experience/authored/<id>.md   accepted change records (lineage)
    <ca_home>/experience/reverted.jsonl     records withdrawn after adoption
    <ca_home>/soul/compose.json             wrapper text paths set by the deployer
    <ca_home>/soul/generations/NNNN.md      every compiled SOUL, never edited
    <ca_home>/soul/generations/NNNN.json    its inputs (bootstrap sha, record ids)
    <ca_home>/soul/current.md               symlink to the active generation

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
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

REPO_ROOT = Path(__file__).resolve().parents[1]
ABSORBED_FILENAME = "absorbed.json"
LEARNED_HEADING = "## Learned in use"


def ca_home() -> Path:
    """Root of all CA runtime state (``$CA_HOME`` or XDG data dir)."""
    override = os.environ.get("CA_HOME")
    if override:
        return Path(override).expanduser()
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "cognitive-assistant"


def soul_dir() -> Path:
    return ca_home() / "soul"


def generations_dir() -> Path:
    return soul_dir() / "generations"


def current_path() -> Path:
    return soul_dir() / "current.md"


def bootstrap_soul_path() -> Path:
    """The SOUL this checkout or package was bootstrapped with."""
    override = os.environ.get("CA_BOOTSTRAP_SOUL")
    if override:
        return Path(override).expanduser()
    return REPO_ROOT / "workspaces" / "alignment" / "artifacts" / "SOUL.md"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def absorbed_ids(bootstrap: Path) -> Set[str]:
    """Record ids the bootstrap SOUL already took into account."""
    path = bootstrap.parent / ABSORBED_FILENAME
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(record_id) for record_id in data.get("records", [])}


def reverted_ids(experience_root: Path) -> Set[str]:
    """Record ids withdrawn after adoption (kept in lineage as negative evidence)."""
    path = experience_root / "reverted.jsonl"
    ids: Set[str] = set()
    if not path.exists():
        return ids
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ids.add(str(json.loads(line)["record"]))
        except (ValueError, KeyError, TypeError):
            continue
    return ids


def parse_authored_source(text: str) -> Dict[str, str]:
    """Split an authored record into front matter fields, title and instruction body."""
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


def active_records(experience_root: Path, bootstrap: Path) -> List[Dict[str, str]]:
    """Accepted records not absorbed by the bootstrap and not reverted, oldest first."""
    authored = experience_root / "authored"
    if not authored.is_dir():
        return []
    skip = absorbed_ids(bootstrap) | reverted_ids(experience_root)
    records = []
    for path in sorted(authored.glob("*.md")):
        record = parse_authored_source(path.read_text(encoding="utf-8"))
        record.setdefault("id", path.stem)
        if record["id"] in skip or not record["instruction"]:
            continue
        records.append(record)
    records.sort(key=lambda record: (record.get("created", ""), record["id"]))
    return records


def lineage_for_bootstrap(experience_root: Optional[Path] = None) -> Dict:
    """Every record ever adopted or withdrawn, for a rebootstrap from source data.

    A rebootstrap does not inherit the previous SOUL, so it sees all accepted
    records (including ones an earlier bootstrap absorbed) with their evidence,
    plus withdrawn records as changes that were tried and reverted.
    """
    from core import experience

    root = experience_root or experience.experience_root()
    authored = root / "authored"
    withdrawn = reverted_ids(root)
    adopted_blocks: List[str] = []
    withdrawn_blocks: List[str] = []
    adopted_ids: List[str] = []
    paths = sorted(authored.glob("*.md")) if authored.is_dir() else []
    for path in paths:
        text = path.read_text(encoding="utf-8").strip()
        record_id = parse_authored_source(text).get("id") or path.stem
        if record_id in withdrawn:
            withdrawn_blocks.append(f'<record id="{record_id}" status="withdrawn">\n{text}\n</record>')
        else:
            adopted_ids.append(record_id)
            adopted_blocks.append(f'<record id="{record_id}" status="adopted">\n{text}\n</record>')
    if not adopted_blocks and not withdrawn_blocks:
        return {"text": "(no lineage: nothing has been adopted in use yet)", "records": []}
    return {"text": "\n\n".join(adopted_blocks + withdrawn_blocks), "records": adopted_ids}


def write_absorbed(bootstrap: Path, record_ids: List[str]) -> Path:
    """Declare which lineage records this bootstrap took into account."""
    path = bootstrap.parent / ABSORBED_FILENAME
    payload = {
        "records": sorted(record_ids),
        "note": "Lineage records this bootstrap SOUL was built with; the living SOUL leaves them out.",
    }
    _atomic_write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def read_compose_config() -> Dict[str, Optional[str]]:
    path = soul_dir() / "compose.json"
    if not path.exists():
        return {"prefix": None, "suffix": None}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"prefix": data.get("prefix"), "suffix": data.get("suffix")}


def write_compose_config(prefix: Optional[str], suffix: Optional[str]) -> Path:
    """Record the deployer's wrapper files so every later compile uses the same ones."""
    path = soul_dir() / "compose.json"
    _atomic_write(path, json.dumps({"prefix": prefix, "suffix": suffix}, indent=2, sort_keys=True) + "\n")
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


def _atomic_write(path: Path, content: str) -> None:
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


def _point_current(generation_file: Path) -> None:
    link = current_path()
    tmp = link.with_name(f".current-{os.getpid()}")
    try:
        tmp.unlink()
    except FileNotFoundError:
        pass
    os.symlink(os.path.relpath(generation_file, link.parent), tmp)
    os.replace(tmp, link)


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


def _journal(event_type: str, payload: Dict) -> None:
    from core import improve

    improve._journal_note(ca_home() / "improve", event_type, payload)


def compile_soul(*, reason: str = "compile", experience_root: Optional[Path] = None) -> Dict:
    """Build the living SOUL from its inputs; new generation only when the output changes."""
    from core import experience

    bootstrap = bootstrap_soul_path()
    bootstrap_text = bootstrap.read_text(encoding="utf-8")
    if not bootstrap_text.strip():
        raise RuntimeError(f"bootstrap SOUL is empty: {bootstrap}")
    root = experience_root or experience.experience_root()
    records = active_records(root, bootstrap)
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
    existing = list_generations()
    number = (max((g["generation"] for g in existing), default=0)) + 1
    meta = {
        "generation": number,
        "sha256": sha,
        "bootstrapSha256": _sha256(bootstrap_text),
        "records": [record["id"] for record in records],
        "createdAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reason": reason,
    }
    generation_file = generations_dir() / f"{number:04d}.md"
    _atomic_write(generation_file, text)
    _atomic_write(generation_file.with_suffix(".json"), json.dumps(meta, indent=2, sort_keys=True) + "\n")
    _point_current(generation_file)
    _journal(
        "soul_compiled",
        {
            "generation": number,
            "output_ref": sha,
            "bootstrap_ref": meta["bootstrapSha256"],
            "record_ids": meta["records"],
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
    _journal("soul_rolled_back", {"generation": generation, "output_ref": meta["sha256"]})
    return meta


def link_into(hermes_home: Path) -> Path:
    """Make ``<hermes_home>/SOUL.md`` a symlink to the living SOUL."""
    link = Path(hermes_home) / "SOUL.md"
    link.parent.mkdir(parents=True, exist_ok=True)
    tmp = link.with_name(f".SOUL.md-{os.getpid()}")
    try:
        tmp.unlink()
    except FileNotFoundError:
        pass
    os.symlink(current_path(), tmp)
    os.replace(tmp, link)
    return link
