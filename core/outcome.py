#!/usr/bin/env python3
"""Outcome check: did the latest living SOUL change make sessions go worse?

The signal is the delayed outcome of a session. Stalled and regressed outcomes
are misses; advanced outcomes are not. Answered (a question settled by the
reply itself), unclear and unscored sessions are excluded. Each eligible Hermes session is attributed to its active generation.
The current generation is compared with the one it replaced:

- pending: either side has fewer than ``min_sessions`` sessions.
- revert:  the miss rate rose and a one-sided two-proportion z-test clears
           ``z_threshold`` (default 1.645, about 95%).
- keep:    enough sessions and no significant rise.

Only one change is under test at a time: a new record is auto-applied only
once the current generation has a verdict. A generation produced by a new
bootstrap is kept without a test; rebootstrapping is the person's call. A
generation that added no records (the deployer's wrapper text changed) does
not end the test of the one before it: their sessions are pooled and the
verdict goes to the generation that added the records.

Every threshold lives in ``OutcomePolicy``.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import AbstractSet, Dict, FrozenSet, List, Optional, Set, Tuple
from urllib.parse import quote

from core import journal, living_soul
from core.paths import improve_dir, soul_dir

VERDICT_SOURCES = frozenset({"desktop", "tui", "cli"})

Outcomes = Tuple[Dict[int, Dict[str, int]], Dict[int, Set[Tuple]]]


@dataclass(frozen=True)
class OutcomePolicy:
    """How a change is judged. The one place these thresholds are set."""

    min_sessions: int = 15
    z_threshold: float = 1.645
    harness: str = "hermes"
    sources: FrozenSet[str] = VERDICT_SOURCES


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


def is_miss(evidence: Dict) -> Optional[bool]:
    """Return None when a session has no decisive outcome."""
    result = evidence.get("outcome")
    if not isinstance(result, dict):
        return None
    label = result.get("label")
    if label in ("stalled", "regressed"):
        return True
    if label == "advanced":
        return False
    return None


def _collect_outcomes(harness: str, sources: AbstractSet[str]) -> Outcomes:
    history = living_soul.activations()
    totals: Dict[int, Dict[str, int]] = {}
    rubrics: Dict[int, Set[Tuple]] = {}
    records: Dict[Tuple[str, str], Dict] = {}
    evidence_dir = improve_dir() / "evidence"
    for path in sorted(evidence_dir.glob("*.json")):
        try:
            evidence = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(evidence, dict) or evidence.get("status") != "ok":
            continue
        identity = (str(evidence.get("harness")), str(evidence.get("transcriptId")))
        qualified = evidence_dir / (quote(identity[0], safe="~!*'()") + ":" + quote(identity[1], safe="~!*'()") + ".json")
        try:
            preferred = json.loads(qualified.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            preferred = None
        records[identity] = preferred if isinstance(preferred, dict) and preferred.get("status") == "ok" else evidence
    for evidence in records.values():
        if evidence.get("harness") != harness:
            continue
        source = evidence.get("source")
        if not isinstance(source, str) or source not in sources:
            continue
        at = evidence.get("sessionAt")
        if not isinstance(at, (int, float)):
            continue
        generation = generation_at(at, history)
        if generation is None:
            continue
        miss = is_miss(evidence)
        if miss is None:
            continue
        bucket = totals.setdefault(generation, {"sessions": 0, "misses": 0})
        bucket["sessions"] += 1
        bucket["misses"] += int(miss)
        rubric = evidence["outcome"].get("rubric")
        if not isinstance(rubric, dict):
            rubric = {}
        prompt, model = rubric.get("promptSha"), rubric.get("model")
        rubrics.setdefault(generation, set()).add((
            prompt if isinstance(prompt, str) and prompt else None,
            model if isinstance(model, str) and model else None,
            rubric.get("matureDays") if isinstance(rubric.get("matureDays"), (int, float)) and not isinstance(rubric.get("matureDays"), bool) and math.isfinite(rubric["matureDays"]) and rubric["matureDays"] >= 0 else None,
        ))
    return totals, rubrics


def collect(policy: OutcomePolicy = OutcomePolicy()) -> Outcomes:
    """Per generation: decisive outcome counts, and the rubrics that scored them."""
    return _collect_outcomes(policy.harness, policy.sources)


def session_outcomes(harness: str = "hermes", sources: Optional[AbstractSet[str]] = None) -> Dict[int, Dict[str, int]]:
    """Per generation: decisive outcome count and sessions with a miss."""
    totals, _ = _collect_outcomes(harness, VERDICT_SOURCES if sources is None else sources)
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
    policy: OutcomePolicy = OutcomePolicy(),
    *,
    record: bool = True,
    collected: Optional[Outcomes] = None,
) -> Dict:
    """Judge the change under test against its parent; settled verdicts are final.

    ``collected`` lets a caller that already read the evidence pass it in.
    """
    current = living_soul.current_generation()
    if not current:
        return {"verdict": "none", "reason": "no living SOUL compiled yet"}
    judged = verdicts()
    settled = judged.get(current["generation"])
    if settled:
        return {**settled, "settled": True}
    # Walk back over generations that added nothing to the one whose records
    # are under test; its sessions and theirs ran with the same records.
    known = {meta["generation"]: meta for meta in living_soul.list_generations()}
    subject, pooled = current, [current["generation"]]
    while (
        not subject.get("added")
        and not subject.get("bootstrapChanged")
        and subject.get("parent") in known
        and subject["parent"] not in judged
    ):
        subject = known[subject["parent"]]
        pooled.append(subject["generation"])
    number, parent = subject["generation"], subject.get("parent")
    base = {"generation": number, "added": subject.get("added", [])}
    if parent is None or subject.get("bootstrapChanged") or not subject.get("added"):
        why = "first generation" if parent is None else (
            "new bootstrap" if subject.get("bootstrapChanged") else "no records added"
        )
        row = {**base, "verdict": "keep", "reason": f"untested: {why}"}
        if record:
            _record_verdict(row)
        return row
    outcomes, rubrics = collected if collected is not None else collect(policy)
    empty = {"sessions": 0, "misses": 0}
    now = {key: sum(outcomes.get(g, empty)[key] for g in pooled) for key in empty}
    before = outcomes.get(parent, empty)
    row = {**base, "parent": parent, "current": now, "baseline": before}
    if now["sessions"] and before["sessions"]:
        used = set().union(*(rubrics.get(g, set()) for g in [*pooled, parent]))
        mismatches = [name for index, name in enumerate(("promptSha", "model", "matureDays"))
                      if len({rubric[index] for rubric in used}) > 1]
        if mismatches:
            return {**row, "verdict": "pending", "reason": "rubric mismatch: " + ", ".join(mismatches)}
    if now["sessions"] < policy.min_sessions or before["sessions"] < policy.min_sessions:
        return {**row, "verdict": "pending", "reason": f"need {policy.min_sessions} sessions on each side"}
    z = z_score(now, before)
    row["z"] = round(z, 3)
    row["improved"] = z < -policy.z_threshold
    row["verdict"] = "revert" if z > policy.z_threshold else "keep"
    if record:
        _record_verdict(row)
    return row
