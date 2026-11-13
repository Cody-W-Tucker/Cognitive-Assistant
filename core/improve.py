#!/usr/bin/env python3
"""The improvement pass: run the Node runtime, review its proposal, adopt records.

The runtime in ``improve/`` (Node, zero dependencies) discovers sessions,
analyzes them and writes a proposal under ``<ca_home>/improve``. This module
launches it (argv in, one JSON proposal on stdout), applies reviewed
decisions, and runs the autonomous judge/revert/adopt step.
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from core import experience, journal, living_soul, outcome, paths
from core.paths import INTERACTION_POSTURE_PATH, REPO_ROOT, atomic_write, improve_dir

RUNTIME_BIN = REPO_ROOT / "improve" / "bin" / "ca-improve.js"

VERDICTS = ("accepted", "rejected", "deferred")
REJECT_REASONS = (
    "too-narrow",
    "too-broad",
    "already-covered",
    "not-evidenced",
    "unsafe",
    "other",
)


def _proposal_path() -> Path:
    return improve_dir() / "proposal.json"


def _runtime(command: str, flags: List[str], *, tui: bool = False) -> Dict:
    """Run one runtime command and return the proposal it prints.

    With ``tui`` the runtime paints progress on the inherited stderr.
    """
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node not found on PATH; run under the repo Nix dev shell, which provides nodejs")
    argv = [
        node,
        str(RUNTIME_BIN),
        command,
        "--state-dir",
        str(improve_dir()),
        "--soul-path",
        str(living_soul.running_soul_path()),
        *flags,
    ]
    proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=None if tui else subprocess.PIPE, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"ca-improve {command} failed: {(proc.stderr or '').strip()}")
    proposal = json.loads(proc.stdout)
    journal.record(
        "run_completed",
        {
            "run_id": str(proposal.get("id", "?")),
            "transcript_count": int(proposal.get("stats", {}).get("transcripts", 0)),
            "resume": command == "synthesize",
        },
    )
    journal.record("proposal_created", {"proposal_id": str(proposal.get("id", "?")), "edit_count": len(proposal.get("edits", []))})
    return proposal


def _write_experience_context() -> Path:
    """The records Hermes is running with (not withdrawn, not absorbed by the bootstrap),
    as the analysis prompt shows them."""
    records = experience.active(exclude=living_soul.absorbed_ids(paths.BOOTSTRAP_SOUL_PATH))
    text = "\n\n".join(
        f'<record id="{record["id"]}">\n# {record["title"]}\n\n{record["instruction"]}\n</record>' for record in records
    )
    path = improve_dir() / "experience-context.md"
    atomic_write(path, (text or "(none yet: nothing has been adopted in use)") + "\n")
    return path


def run(
    *,
    tui: bool = False,
    home: Optional[Path] = None,
    since: str = "30d",
    analyzer: str = "model",
    min_gap_evidence: int = 2,
    harnesses: Optional[List[str]] = None,
) -> Dict:
    """Discover and analyze new sessions, then propose records. Writes only under CA home.

    ``home`` scopes discovery to one directory; without it the runtime finds
    stores via HERMES_HOME / CLAUDE_CONFIG_DIR / CODEX_HOME.
    """
    flags = [
        "--tui" if tui else "--headless",
        "--experience-file",
        str(_write_experience_context()),
        "--posture-path",
        str(INTERACTION_POSTURE_PATH),
        "--since",
        since,
        "--analyzer",
        analyzer,
        "--min-gap-evidence",
        str(min_gap_evidence),
    ]
    if home is not None:
        flags += ["--home", str(home)]
    for harness in harnesses or []:
        flags += ["--harness", harness]
    return _runtime("run", flags, tui=tui)


def synthesize_resume(*, min_gap_evidence: int = 2) -> Dict:
    """Propose again from evidence already on disk, without discovering or analyzing sessions."""
    return _runtime("synthesize", ["--min-gap-evidence", str(min_gap_evidence)])


def read_proposal() -> Dict:
    path = _proposal_path()
    if not path.exists():
        raise RuntimeError("no proposal to apply; run `python -m core improve-run --headless` first")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_decisions(values: List[str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Parse ``["e1=accepted", "e2=rejected:too-narrow"]`` into (verdicts, reject reasons)."""
    decisions: Dict[str, str] = {}
    reasons: Dict[str, str] = {}
    for value in values:
        for token in value.split():
            if "=" not in token:
                raise RuntimeError(f"bad decision {token!r}; want <edit>=accepted|rejected[:reason]")
            edit_id, _, verdict = token.partition("=")
            verdict, _, reason = verdict.partition(":")
            if edit_id in decisions:
                raise RuntimeError(f"decision names {edit_id!r} twice")
            if verdict not in ("accepted", "rejected"):
                raise RuntimeError(f"bad verdict {verdict!r} for {edit_id!r}")
            if reason and (verdict != "rejected" or reason not in REJECT_REASONS):
                raise RuntimeError(f"bad reason {reason!r} for {edit_id!r} (reasons: {', '.join(REJECT_REASONS)})")
            decisions[edit_id] = verdict
            if reason:
                reasons[edit_id] = reason
    return decisions, reasons


def review_in_terminal(proposal: Dict) -> Dict[str, str]:
    """Show each candidate in full (evidence, record) and ask accept/reject."""
    if not sys.stdin.isatty():
        raise RuntimeError("proposal is unreviewed: pass --decisions or run in a terminal for review")
    edits = proposal.get("edits", [])
    decisions: Dict[str, str] = {}
    for index, edit in enumerate(edits, start=1):
        record = edit.get("record") or {}
        print(f"\n{'=' * 72}")
        print(f"Candidate {index}/{len(edits)} === {edit['id']}: {edit.get('title', '')} ===")
        print(f"{'=' * 72}")
        print(f"kind: {edit.get('kind', '')}")
        print(f"rationale: {edit.get('rationale', '')}")
        print("--- candidate record ---")
        for field in ("id", "title", "body", "clusterId", "counterevidence", "compilerImplication"):
            print(f"    {field}: {record.get(field, '')}")
        print(f"    sources: {', '.join(record.get('sources', []))}")
        evidence = record.get("evidence", [])
        print(f"    evidence ({len(evidence)}):")
        for item in evidence:
            print(f"    - ({item.get('source', '?')}) {item.get('text', '')}")
        print(f"{'=' * 72}")
        while True:
            answer = input(f"{edit['id']} [accept/reject]? ").strip().lower()
            if answer in ("accept", "a"):
                decisions[edit["id"]] = "accepted"
                break
            if answer in ("reject", "r"):
                decisions[edit["id"]] = "rejected"
                break
    return decisions


@contextmanager
def _apply_lock() -> Iterator[None]:
    """Fail a second concurrent apply instead of letting both write."""
    path = improve_dir() / ".apply.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(f"another improve-apply holds {path}; retry when it finishes") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _check_decisions(edits: List[Dict], decisions: Dict[str, str], reasons: Dict[str, str]) -> None:
    edit_ids = [edit["id"] for edit in edits]
    for edit_id in list(decisions) + list(reasons):
        if edit_id not in edit_ids:
            raise RuntimeError(f"decision names unknown edit {edit_id!r} (edits: {', '.join(edit_ids)})")
    undecided = [edit_id for edit_id in edit_ids if edit_id not in decisions]
    if undecided:
        raise RuntimeError(f"proposal is unreviewed: no decision for {', '.join(undecided)}")
    for edit in edits:
        verdict = decisions[edit["id"]]
        if verdict not in VERDICTS:
            raise RuntimeError(f"bad verdict {verdict!r} for {edit['id']!r}")
        annotation = (edit.get("annotation") or {}).get("verdict")
        if annotation not in ("keep", "drop", "revert"):
            raise RuntimeError(f"edit {edit['id']} has no final annotation; only annotated records can be applied")
        if verdict == "accepted":
            if annotation != "keep":
                raise RuntimeError(f"edit {edit['id']} cannot be accepted (annotation verdict is {annotation!r}, want 'keep')")
            if not experience.is_complete(edit.get("record") or {}):
                raise RuntimeError(f"edit {edit['id']} record is incomplete; want every field in {experience.RECORD_FIELDS}")


def apply(
    *,
    decisions: Optional[Dict[str, str]] = None,
    reasons: Optional[Dict[str, str]] = None,
    dry_run: bool = False,
    expected_proposal_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> Dict:
    """Record a reviewed proposal: write accepted records, log rejections, rebuild the living SOUL.

    Every edit needs a verdict. ``deferred`` edits are neither written nor
    rejected, so a later run can propose them again on fresh evidence.
    Without ``decisions`` the proposal is reviewed in the terminal.
    """
    proposal = read_proposal()
    proposal_id = proposal.get("id", "?")
    if expected_proposal_id is not None and proposal_id != expected_proposal_id:
        raise RuntimeError(
            f"proposal on disk is {proposal_id}, not {expected_proposal_id};"
            " a newer run replaced the one you reviewed. Review the current proposal."
        )
    if proposal.get("appliedAt"):
        raise RuntimeError(
            f"proposal {proposal_id} was already applied ({proposal['appliedAt']}); run improve-run again for a fresh one"
        )
    edits = proposal.get("edits", [])
    if not edits:
        return {"accepted": [], "rejected": [], "written": [], "dry_run": dry_run, "generation": None}
    decisions = dict(decisions) if decisions is not None else review_in_terminal(proposal)
    reasons = dict(reasons or {})
    _check_decisions(edits, decisions, reasons)
    accepted = [edit for edit in edits if decisions[edit["id"]] == "accepted"]
    rejected = [edit for edit in edits if decisions[edit["id"]] == "rejected"]
    result = {
        "accepted": [edit["id"] for edit in accepted],
        "rejected": [edit["id"] for edit in rejected],
        "written": [],
        "dry_run": dry_run,
        "generation": None,
    }
    if dry_run:
        return result
    with _apply_lock():
        current = read_proposal()
        if current.get("id") != proposal_id or current.get("appliedAt"):
            raise RuntimeError(f"proposal {proposal_id} changed or was applied while waiting; review the current proposal")
        _write_decisions(proposal, accepted, rejected, decisions, reasons, result["written"])
    for edit in accepted:
        journal.record(
            "experience_accepted",
            {
                "proposal_id": proposal_id,
                "edit_id": edit["id"],
                "record_id": edit["record"]["id"],
                "sources": journal.sanitize_sources(edit["record"]["sources"]),
            },
        )
    for edit in rejected:
        journal.record(
            "proposal_rejected",
            {"proposal_id": proposal_id, "edit_id": edit["id"], "reason": reasons.get(edit["id"], "other")},
        )
    if accepted:
        result["generation"] = living_soul.compile_soul(reason=reason or f"accepted {proposal_id}")
    return result


def _rejection_row(at: str, proposal_id: str, edit_id: str, reason: str, record: Dict) -> Dict:
    """One rejections.jsonl row; the runtime suppresses a candidate matching its cluster or
    title unless the candidate cites sessions the rejection did not."""
    return {
        "at": at,
        "proposal": proposal_id,
        "edit": edit_id,
        "reason": reason,
        "title": record.get("title", ""),
        "clusterId": record.get("clusterId", ""),
        "recordId": record.get("id", ""),
        "sources": list(record.get("sources", [])),
    }


def _append_rejections(rows: List[Dict]) -> None:
    path = improve_dir() / "rejections.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _write_decisions(
    proposal: Dict,
    accepted: List[Dict],
    rejected: List[Dict],
    decisions: Dict[str, str],
    reasons: Dict[str, str],
    written: List[str],
) -> None:
    """Write records, rejections and the applied proposal, or restore every file touched.

    A half-applied proposal would leave records the next SOUL compile adopts
    with no review on record, so a failure puts everything back.
    """
    rejections_path = improve_dir() / "rejections.jsonl"
    touched = [experience.record_path(edit["record"]["id"]) for edit in accepted] + [rejections_path, _proposal_path()]
    backups = {path: path.read_bytes() if path.exists() else None for path in touched}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        for edit in accepted:
            written.append(str(experience.write(edit["record"], edit, proposal.get("id", "?"))))
        _append_rejections(
            [
                _rejection_row(
                    now,
                    proposal.get("id", "?"),
                    edit["id"],
                    reasons.get(edit["id"], "other"),
                    {**(edit.get("record") or {}), "title": (edit.get("record") or {}).get("title") or edit.get("title", "")},
                )
                for edit in rejected
            ]
        )
        applied = {**proposal, "reviewed": True, "appliedAt": now, "decisions": decisions}
        atomic_write(_proposal_path(), json.dumps(applied, indent=2) + "\n")
    except BaseException:
        for path, data in backups.items():
            if data is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(data)
        written.clear()
        raise


def _auto_candidate(proposal: Dict) -> Optional[Dict]:
    """First edit the annotation stage kept with a complete record that was never withdrawn."""
    withdrawn = experience.reverted_ids()
    for edit in proposal.get("edits", []):
        record = edit.get("record") or {}
        if (
            (edit.get("annotation") or {}).get("verdict") == "keep"
            and experience.is_complete(record)
            and record["id"] not in withdrawn
        ):
            return edit
    return None


def auto_cycle(*, proposal: Dict, min_sessions: int = 15, z_threshold: float = 1.645) -> Dict:
    """One autonomous step after a headless run: judge, revert, or adopt one change.

    1. Judge the active generation against its parent (core.outcome).
    2. revert -> withdraw the records it added and compile without them.
    3. pending -> adopt nothing; one change is under test at a time.
    4. keep -> once the active generation has ``min_sessions`` of its own
       (the baseline the next change is judged against), adopt the first
       kept record from this run's proposal.
    """
    if living_soul.current_generation() is None:
        living_soul.compile_soul(reason="auto: initial")
    verdict = outcome.evaluate(min_sessions=min_sessions, z_threshold=z_threshold)
    result: Dict = {"verdict": verdict, "action": "none", "generation": None, "records": []}
    current = living_soul.current_generation()["generation"]
    if verdict["verdict"] == "revert":
        added = list(verdict.get("added", []))
        reason = f"miss rate rose (z={verdict.get('z')})"
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        rows = []
        for record_id in added:
            stored = experience.read(record_id)
            record = {
                "id": record_id,
                "title": stored.get("title", ""),
                "clusterId": stored.get("cluster", ""),
                "sources": [s.strip() for s in stored.get("sources", "").split(",") if s.strip()],
            }
            rows.append(_rejection_row(now, stored.get("proposal", "?"), "auto-revert", "reverted", record))
        _append_rejections(rows)
        meta = living_soul.revert_records(added, reason=reason)
        result.update(action="revert", records=added, generation=meta["generation"])
    elif verdict["verdict"] == "pending":
        result["action"] = "wait"
    elif outcome.session_outcomes().get(current, {}).get("sessions", 0) < min_sessions:
        result["action"] = "baseline"
    else:
        candidate = _auto_candidate(proposal)
        if candidate is not None and not proposal.get("appliedAt"):
            decisions = {edit["id"]: "deferred" for edit in proposal["edits"]}
            decisions[candidate["id"]] = "accepted"
            applied = apply(
                decisions=decisions,
                expected_proposal_id=proposal.get("id"),
                reason=f"auto-apply {candidate['record']['id']}"[:80],
            )
            result.update(
                action="adopt",
                records=[candidate["record"]["id"]],
                generation=(applied["generation"] or {}).get("generation"),
            )
    journal.record(
        "auto_cycle",
        {
            "verdict": str(verdict.get("verdict")),
            "kind": result["action"],
            "generation": result["generation"],
            "record_ids": result["records"],
        },
    )
    return result
