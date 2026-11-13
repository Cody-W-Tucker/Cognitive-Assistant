#!/usr/bin/env python3
"""Private lineage journal of what the improvement loop did.

Append-only JSONL history at ``<stateDir>/journal/events.jsonl`` with
derived deterministic views (``current.json``, ``bootstrap.md``).

Contract:
- ``events.jsonl`` is append-only history; ``current.json``/``bootstrap.md``
  are generated views (regenerable via :func:`compact`).
- Sanitized before EVERY write: rejects raw transcripts/prompts/evidence
  quotes/full SOUL/credentials/absolute paths in events and excludes them
  from generated views.
- It only writes under ``<stateDir>/journal`` and never deletes anything else.
- Payloads may carry ``sources``/``source_refs`` as short id refs only;
  no KB Markdown rendering (views list refs as plain text).
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List

from core.paths import improve_dir

JOURNAL_DIRNAME = "journal"
EVENTS_FILENAME = "events.jsonl"
CURRENT_FILENAME = "current.json"
BOOTSTRAP_FILENAME = "bootstrap.md"

ALLOWED_TYPES = frozenset(
    {
        "run_completed",
        "proposal_created",
        "experience_accepted",
        "proposal_rejected",
        "artifact_compiled",  # no longer emitted; kept so older journals still read
        "soul_compiled",
        "soul_rolled_back",
        "soul_verdict",
        "auto_cycle",
    }
)

FORBIDDEN_KEYS = frozenset(
    {
        "transcript",
        "transcripts",
        "prompt",
        "prompts",
        "evidence",
        "evidence_quote",
        "evidence_quotes",
        "quote",
        "quotes",
        "text",
        "content",
        "body",
        "soul",
        "soul_text",
        "full_soul",
        "stagedartifact",
        "staged_artifact",
        "diff",
        "record",
        "record_body",
        "credential",
        "credentials",
        "secret",
        "password",
        "token",
        "api_key",
        "apikey",
        "private_key",
        "bearer",
        "auth",
    }
)

_CREDENTIAL_RE = re.compile(
    r"(api[_-]?key|passwd|password|secret|bearer\s+[A-Za-z0-9._~-]+"
    r"|sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]+|xox[bpas]-"
    r"|BEGIN [A-Z ]*PRIVATE KEY)",
    re.IGNORECASE,
)
_ABSOLUTE_PATH_RE = re.compile(r"/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+")

MAX_STRING_CHARS = 2000
MAX_ID_CHARS = 200
MAX_SOURCES = 50

_FORBIDDEN_LOWERED = frozenset(str(k).lower() for k in FORBIDDEN_KEYS)


def _normalize_key(key: Any) -> str:
    """Lowercase and strip _, -, space so equivalent spellings match."""
    return re.sub(r"[_\-\s]+", "", str(key).lower())


_NORMALIZED_FORBIDDEN = frozenset(_normalize_key(k) for k in FORBIDDEN_KEYS)

_CREDENTIAL_SUBSTRINGS = frozenset(
    {
        "apikey",
        "privatekey",
        "secret",
        "password",
        "passwd",
        "credential",
        "bearer",
        "authtoken",
        "token",
    }
)

# Lifecycle id/count refs that contain a raw stem but carry no raw content.
_SAFE_EXPLICIT_KEYS = frozenset(
    {
        "run_id",
        "proposal_id",
        "edit_id",
        "record_id",
        "transcript_count",
        "edit_count",
        "sources",
        "source_refs",
        "analyzer",
        "resume",
        "reason",
        "kind",
        "title",
        "note",
    }
)
_SAFE_SUFFIXES = ("_id", "_ids", "_count", "_counts", "_ref", "_refs")


def _is_forbidden_key(key: Any) -> bool:
    """Reject forbidden-like names at any depth, normalizing case/separators."""
    lowered = str(key).lower()
    normalized = _normalize_key(key)
    if normalized in _NORMALIZED_FORBIDDEN:
        return True
    if any(sub in normalized for sub in _CREDENTIAL_SUBSTRINGS):
        return True
    parts = [p for p in re.split(r"[_\-\s]+", lowered) if p]
    if any(p in _FORBIDDEN_LOWERED for p in parts):
        if lowered in _SAFE_EXPLICIT_KEYS or lowered.endswith(_SAFE_SUFFIXES):
            return False
        return True
    return False


def _check_key(key: Any) -> None:
    if _is_forbidden_key(key):
        raise ValueError(f"journal payload key {key!r} is forbidden (raw content excluded)")


def journal_dir(state_dir: Path) -> Path:
    """Return the journal directory for a state dir."""
    return Path(state_dir) / JOURNAL_DIRNAME


def _ensure_journal_dir(state_dir: Path) -> Path:
    directory = journal_dir(state_dir)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(directory, 0o700)
    except OSError:
        pass
    return directory


def _restrict_file(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _check_view_text(value: str, field: str) -> None:
    """Pattern checks for derived views regardless of aggregate size.

    Aggregate views grow with history, so no length cap applies here;
    absolute-path and credential patterns are still rejected.
    """
    if _ABSOLUTE_PATH_RE.search(value):
        raise ValueError(f"journal view {field!r} contains absolute path")
    if _CREDENTIAL_RE.search(value):
        raise ValueError(f"journal view {field!r} contains credentials")


def _physical_line_count(events_path: Path, fallback: int) -> int:
    """Count physical nonempty JSONL lines so IDs stay unique with corruption.

    ``read_events`` skips malformed lines; counting raw nonempty lines keeps
    the deterministic append index collision-free without rewriting history.
    """
    try:
        raw = events_path.read_text(encoding="utf-8")
    except OSError:
        return fallback
    return sum(1 for line in raw.splitlines() if line.strip())


def _check_string(value: str, field: str) -> None:
    if len(value) > MAX_STRING_CHARS:
        raise ValueError(f"journal payload field {field!r} too long (full text excluded)")
    if _ABSOLUTE_PATH_RE.search(value):
        raise ValueError(f"journal payload field {field!r} contains absolute path")
    stripped = value.strip()
    if len(stripped) > 1 and stripped.startswith("/") and " " not in stripped[:40]:
        raise ValueError(f"journal payload field {field!r} contains absolute path")
    if _CREDENTIAL_RE.search(value):
        raise ValueError(f"journal payload field {field!r} contains credentials")


def _validate_payload(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("journal payload must be an object")
    for key, value in payload.items():
        _check_key(key)
        _validate_value(value, field=str(key))


def _validate_value(value: Any, field: str) -> None:
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, str):
        _check_string(value, field)
        return
    if isinstance(value, list):
        if len(value) > MAX_SOURCES + 10:
            raise ValueError(f"journal payload field {field!r} list too long")
        for item in value:
            _validate_value(item, field=field)
        return
    if isinstance(value, dict):
        for sub_key, sub_value in value.items():
            _check_key(sub_key)
            _validate_value(sub_value, field=f"{field}.{sub_key}")
        return
    raise ValueError(f"journal payload field {field!r} has unsupported type {type(value).__name__}")


def _validate_event(event: Dict[str, Any]) -> None:
    event_type = event.get("type")
    if event_type not in ALLOWED_TYPES:
        raise ValueError(f"unknown journal event type {event_type!r}")
    payload = event.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("journal event payload must be an object")
    _validate_payload(payload)


def _sanitize_ref(value: Any) -> str | None:
    """Keep only short plain id refs (no paths/markdown); else None."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > MAX_ID_CHARS:
        return None
    if _ABSOLUTE_PATH_RE.search(text) or _CREDENTIAL_RE.search(text):
        return None
    if text.startswith("/") or text.startswith("~"):
        return None
    if "\n" in text or "[" in text or "]" in text or "(" in text or ")" in text:
        return None
    return text


def sanitize_sources(values: Any) -> List[str]:
    """Filter a sources list down to safe short refs (excludes the rest)."""
    if not isinstance(values, list):
        return []
    kept: List[str] = []
    for item in values[:MAX_SOURCES]:
        ref = _sanitize_ref(item)
        if ref:
            kept.append(ref)
    return kept


def read_events(state_dir: Path) -> List[Dict[str, Any]]:
    """Tolerant read of journal events: missing/malformed lines are skipped."""
    path = journal_dir(Path(state_dir)) / EVENTS_FILENAME
    if not path.exists():
        return []
    events: List[Dict[str, Any]] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(parsed, dict):
            continue
        try:
            _validate_event(parsed)
        except ValueError:
            continue
        events.append(parsed)
    return events


@contextmanager
def _locked(state_dir: Path) -> Iterator[Path]:
    """Hold the journal's exclusive lock; yields the journal directory."""
    directory = _ensure_journal_dir(Path(state_dir))
    lock_path = directory / ".journal.lock"
    with open(lock_path, "a+", encoding="utf-8") as lock:
        _restrict_file(lock_path)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield directory
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def append_event(state_dir: Path, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate then append one event; regenerates views. Rejects forbidden content."""
    _validate_event({"type": event_type, "payload": payload})
    base = Path(state_dir)
    with _locked(base) as directory:
        events_path = directory / EVENTS_FILENAME
        next_index = _physical_line_count(events_path, fallback=len(read_events(base))) + 1
        event = {
            "id": f"evt-{next_index:06d}",
            "type": event_type,
            "at": _utcnow(),
            "payload": json.loads(json.dumps(payload, sort_keys=True)),
        }
        with open(events_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        _restrict_file(events_path)
        _regen_views_unlocked(base, directory)
    return event


def record(event_type: str, payload: Dict[str, Any]) -> None:
    """Append to CA home's journal. The journal is a record of what happened,
    so failing to write it warns instead of undoing the change it describes."""
    try:
        append_event(improve_dir(), event_type, payload)
    except (OSError, ValueError) as exc:
        print(f"warning: journal event {event_type} not recorded: {exc}", file=sys.stderr)


def _summarize(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_type: Dict[str, int] = {}
    accepted: List[str] = []
    rejected: List[str] = []
    proposals: List[str] = []
    runs: List[str] = []
    source_refs: List[str] = []
    def keep(bucket: List[str], value: Any) -> None:
        ref = _sanitize_ref(value)
        if ref and ref not in bucket:
            bucket.append(ref)

    for event in events:
        event_type = str(event.get("type"))
        by_type[event_type] = by_type.get(event_type, 0) + 1
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        keep(runs, payload.get("run_id"))
        keep(proposals, payload.get("proposal_id"))
        if event_type == "experience_accepted":
            keep(accepted, payload.get("record_id"))
        if event_type == "proposal_rejected":
            keep(rejected, payload.get("edit_id"))
        sources = payload.get("sources", payload.get("source_refs", []))
        for item in sources if isinstance(sources, list) else []:
            keep(source_refs, item)
    last = events[-1] if events else None
    summary: Dict[str, Any] = {
        "event_count": len(events),
        "by_type": dict(sorted(by_type.items())),
        "accepted": sorted(accepted),
        "rejected": sorted(rejected),
        "proposals": sorted(proposals),
        "runs": sorted(runs),
        "source_refs": sorted(source_refs),
        "last": (
            {"id": last.get("id"), "type": last.get("type"), "at": last.get("at")}
            if last
            else None
        ),
        "note": "journal views generated; events.jsonl is append-only history",
    }
    return summary


def _render_bootstrap(summary: Dict[str, Any]) -> str:
    lines = [
        "# Lineage Bootstrap",
        "",
        "_Generated view. `events.jsonl` is append-only history; this file is regenerated._",
        "",
        f"Events: {summary['event_count']}",
        "",
        "## Counts by type",
        "",
    ]
    by_type = summary.get("by_type", {})
    if by_type:
        for key in sorted(by_type):
            lines.append(f"- {key}: {by_type[key]}")
    else:
        lines.append("- (no events yet)")
    lines.extend(
        [
            "",
            "## Accepted experience",
            "",
        ]
    )
    accepted = summary.get("accepted", [])
    lines.extend([f"- {item}" for item in accepted] or ["- (none)"])
    lines.extend(["", "## Rejected proposals", ""])
    rejected = summary.get("rejected", [])
    lines.extend([f"- {item}" for item in rejected] or ["- (none)"])
    lines.extend(["", "## Proposals", ""])
    proposals = summary.get("proposals", [])
    lines.extend([f"- {item}" for item in proposals] or ["- (none)"])
    lines.extend(["", "## Source refs (ids only, no KB rendering)", ""])
    refs = summary.get("source_refs", [])
    lines.extend([f"- {item}" for item in refs] or ["- (none)"])
    lines.append("")
    return "\n".join(lines)


def _regen_views_unlocked(base: Path, directory: Path) -> Dict[str, Any]:
    """Regenerate views; caller must hold the journal lock."""
    summary = _summarize(read_events(base))
    current_text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    bootstrap_text = _render_bootstrap(summary)
    for name, text in ((CURRENT_FILENAME, current_text), (BOOTSTRAP_FILENAME, bootstrap_text)):
        _check_view_text(text, name)
        path = directory / name
        path.write_text(text, encoding="utf-8")
        _restrict_file(path)
    return summary


def compact(state_dir: Path) -> Dict[str, Any]:
    """Regenerate views from the events that still parse; touches nothing outside journal/."""
    base = Path(state_dir)
    with _locked(base) as directory:
        return _regen_views_unlocked(base, directory)
