#!/usr/bin/env python3
"""Outcome check: did the latest living SOUL change make sessions go worse?

The signal is what already went wrong in real sessions, as the analysis pass
records it: a session is a *miss* when it has at least one quote-backed
negative (harm or non-compliance) or gap. Each analyzed Hermes session is
attributed to the generation that was active when it happened. The current
generation is compared with the one it replaced:

- pending: either side has fewer than ``min_sessions`` sessions.
- revert:  the miss rate rose and a one-sided two-proportion z-test clears
           ``z_threshold`` (default 1.645, about 95%).
- keep:    enough sessions and no significant rise.

Only one change is under test at a time: a new record is auto-applied only
once the current generation has a verdict. A generation produced by a new
bootstrap is kept without a test; rebootstrapping is the person's call.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core import journal, living_soul
from core.paths import improve_dir, soul_dir

MISS_CLASSES = {"harm", "non-compliance"}


def _parse_at(value: str) -> float:
    return datetime.fromisoformat(value).timestamp() * 1000


def generation_at(ms: float, history: List[Dict]) -> Optional[int]:
    """Generation active at ``ms`` (epoch millis), from the activation history."""
    active = None
    for row in history:
        if _parse_at(row["at"]) <= ms:
            active = row["generation"]
        else:
            break
    return active


def is_miss(evidence: Dict) -> bool:
    negatives = [n for n in evidence.get("negative", []) or [] if n.get("class") in MISS_CLASSES]
    return bool(negatives or evidence.get("gaps"))


def session_outcomes(harness: str = "hermes") -> Dict[int, Dict[str, int]]:
    """Per generation: analyzed session count and sessions with a miss."""
    history = living_soul.activations()
    totals: Dict[int, Dict[str, int]] = {}
    for path in sorted((improve_dir() / "evidence").glob("*.json")):
        try:
            evidence = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if evidence.get("status") != "ok" or evidence.get("harness") != harness:
            continue
        at = evidence.get("sessionAt")
        if not isinstance(at, (int, float)):
            continue
        generation = generation_at(at, history)
        if generation is None:
            continue
        bucket = totals.setdefault(generation, {"sessions": 0, "misses": 0})
        bucket["sessions"] += 1
        bucket["misses"] += int(is_miss(evidence))
    return totals


def _verdicts_path() -> Path:
    return soul_dir() / "verdicts.jsonl"


def verdicts() -> Dict[int, Dict]:
    path = _verdicts_path()
    if not path.exists():
        return {}
    out: Dict[int, Dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        out[int(row["generation"])] = row
    return out


def _record_verdict(row: Dict) -> None:
    path = _verdicts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    journal.record(
        "soul_verdict",
        {
            "generation": row["generation"],
            "verdict": row["verdict"],
            "current_sessions": row.get("current", {}).get("sessions", 0),
            "current_misses": row.get("current", {}).get("misses", 0),
            "baseline_sessions": row.get("baseline", {}).get("sessions", 0),
            "baseline_misses": row.get("baseline", {}).get("misses", 0),
            "record_ids": row.get("added", []),
        },
    )


def z_score(current: Dict[str, int], baseline: Dict[str, int]) -> float:
    """One-sided z for 'current miss rate is higher than baseline'."""
    n1, n2 = current["sessions"], baseline["sessions"]
    p1, p2 = current["misses"] / n1, baseline["misses"] / n2
    pooled = (current["misses"] + baseline["misses"]) / (n1 + n2)
    spread = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if spread == 0:
        return 0.0
    return (p1 - p2) / spread


def evaluate(
    *,
    min_sessions: int = 15,
    z_threshold: float = 1.645,
    record: bool = True,
) -> Dict:
    """Judge the active generation against its parent; settled verdicts are final."""
    current = living_soul.current_generation()
    if not current:
        return {"verdict": "none", "reason": "no living SOUL compiled yet"}
    number = current["generation"]
    settled = verdicts().get(number)
    if settled:
        return {**settled, "settled": True}
    parent = current.get("parent")
    base = {"generation": number, "added": current.get("added", [])}
    if parent is None or current.get("bootstrapChanged") or not current.get("added"):
        why = "first generation" if parent is None else (
            "new bootstrap" if current.get("bootstrapChanged") else "no records added"
        )
        row = {**base, "verdict": "keep", "reason": f"untested: {why}"}
        if record:
            _record_verdict(row)
        return row
    outcomes = session_outcomes()
    empty = {"sessions": 0, "misses": 0}
    now, before = outcomes.get(number, empty), outcomes.get(parent, empty)
    row = {**base, "parent": parent, "current": now, "baseline": before}
    if now["sessions"] < min_sessions or before["sessions"] < min_sessions:
        return {**row, "verdict": "pending", "reason": f"need {min_sessions} sessions on each side"}
    z = z_score(now, before)
    row["z"] = round(z, 3)
    row["verdict"] = "revert" if z > z_threshold else "keep"
    if record:
        _record_verdict(row)
    return row
