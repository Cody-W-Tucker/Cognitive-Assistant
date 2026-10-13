#!/usr/bin/env python3
"""Narrow Python boundary to the CA improvement JS runtime.

The runtime lives in ``improve/`` (Node, zero dependencies). This module is
the only caller: argv + environment in, JSON on stdout out. It never imports
model clients and never touches transcript stores itself.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core import experience

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_BIN = REPO_ROOT / "improve" / "bin" / "ca-improve.js"

REJECT_REASONS = (
    "too-narrow",
    "too-broad",
    "already-covered",
    "not-evidenced",
    "unsafe",
    "other",
)


def node_bin() -> str:
    """Return the Node binary, or raise with the Nix dev-shell hint."""
    found = shutil.which("node")
    if found:
        return found
    raise RuntimeError(
        "node not found on PATH; run under the repo Nix dev shell "
        "(nix develop --command ...) which provides nodejs"
    )


def default_state_dir() -> Path:
    """Return the XDG-backed private state dir for the improve runtime."""
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "cognitive-assistant" / "improve"


def discover_transcripts(
    *,
    home: Path,
    cwd: Path,
    state_dir: Path,
    since: str = "30d",
    harnesses: Optional[List[str]] = None,
) -> Dict:
    """Discover global transcripts via the JS runtime; CWD-independent."""
    cmd = [
        node_bin(),
        str(RUNTIME_BIN),
        "discover",
        "--home",
        str(home),
        "--state-dir",
        str(state_dir),
        "--since",
        since,
    ]
    for harness in harnesses or []:
        cmd.extend(["--harness", harness])
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ca-improve discover failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def run_headless(
    *,
    home: Path,
    cwd: Path,
    state_dir: Optional[Path] = None,
    since: str = "30d",
    analyzer: str = "acpx",
    soul_path: Optional[Path] = None,
    min_gap_evidence: int = 2,
) -> Dict:
    """Run the headless improvement pass; returns the proposal dict.

    All runtime state lands under ``state_dir`` (default XDG). The pass never
    writes into the CA repo and never deploys to Hermes.
    """
    resolved_state = state_dir or default_state_dir()
    cmd = [
        node_bin(),
        str(RUNTIME_BIN),
        "run",
        "--headless",
        "--home",
        str(home),
        "--state-dir",
        str(resolved_state),
        "--since",
        since,
        "--analyzer",
        analyzer,
        "--min-gap-evidence",
        str(min_gap_evidence),
    ]
    if soul_path is not None:
        cmd.extend(["--soul-path", str(soul_path)])
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ca-improve run failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def run_tui(
    *,
    home: Path,
    cwd: Path,
    state_dir: Optional[Path] = None,
    since: str = "30d",
    analyzer: str = "acpx",
    soul_path: Optional[Path] = None,
    min_gap_evidence: int = 2,
) -> Dict:
    """Run live stderr progress while preserving stdout's one JSON proposal."""
    resolved_state = state_dir or default_state_dir()
    cmd = [
        node_bin(), str(RUNTIME_BIN), "run", "--tui", "--home", str(home),
        "--state-dir", str(resolved_state), "--since", since, "--analyzer", analyzer,
        "--min-gap-evidence", str(min_gap_evidence),
    ]
    if soul_path is not None:
        cmd.extend(["--soul-path", str(soul_path)])
    # Inherit stderr: the Node view must paint the actual terminal. stdout is
    # captured solely for the proposal handoff to the Python review route.
    proc = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError("ca-improve TUI run failed")
    return json.loads(proc.stdout)


def read_proposal(state_dir: Path) -> Dict:
    """Read the headless proposal from private state, or raise."""
    proposal_path = state_dir / "proposal.json"
    if not proposal_path.exists():
        raise RuntimeError(
            "no proposal to apply; run `python -m core improve-run --headless` first"
        )
    return json.loads(proposal_path.read_text(encoding="utf-8"))


def parse_decisions(values: List[str], edit_ids: List[str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Parse a decisions vector like ["e1=accepted", "e2=rejected:too-narrow"]."""
    decisions: Dict[str, str] = {}
    reasons: Dict[str, str] = {}
    for value in values:
        for token in value.split():
            if "=" not in token:
                raise RuntimeError(f"bad decision {token!r}; want <edit>=accepted|rejected[:reason]")
            edit_id, _, verdict = token.partition("=")
            verdict, _, reason = verdict.partition(":")
            if edit_id not in edit_ids:
                raise RuntimeError(f"decision names unknown edit {edit_id!r} (edits: {', '.join(edit_ids)})")
            if edit_id in decisions:
                raise RuntimeError(f"decision names {edit_id!r} twice")
            if verdict not in ("accepted", "rejected"):
                raise RuntimeError(f"bad verdict {verdict!r} for {edit_id!r}")
            if reason and (verdict != "rejected" or reason not in REJECT_REASONS):
                raise RuntimeError(
                    f"bad reason {reason!r} for {edit_id!r} (reasons: {', '.join(REJECT_REASONS)})"
                )
            decisions[edit_id] = verdict
            if reason:
                reasons[edit_id] = reason
    return decisions, reasons


def review_in_terminal(proposal: Dict) -> Dict[str, str]:
    """Backpass-like terminal TUI: full evidence/record/diff per candidate.

    Stdlib only (no heavy TUI dependency): sectioned full-text review with
    per-candidate navigation. Shows every evidence item untruncated, the full
    candidate experience record, the full staged generated artifact, and the
    staged diff. Headless runs never call this; they emit JSON on stdout.
    """
    if not sys.stdin.isatty():
        raise RuntimeError(
            "proposal is unreviewed: pass --decisions or run in a terminal for review"
        )
    edits = proposal.get("edits", [])
    total = len(edits)
    decisions: Dict[str, str] = {}
    for index, edit in enumerate(edits, start=1):
        print(f"\n{'=' * 72}")
        print(f"Candidate {index}/{total} === {edit['id']}: {edit.get('title', '')} ===")
        print(f"{'=' * 72}")
        print(f"kind: {edit.get('kind', '')}")
        print(f"rationale: {edit.get('rationale', '')}")
        instructions = edit.get("instructions", [])
        if instructions:
            print("--- instructions ---")
            for instruction in instructions:
                print(f"  * {instruction}")
        evidence = edit.get("evidence", [])
        print(f"--- evidence ({len(evidence)} items, untruncated) ---")
        for item in evidence:
            print(f"  - ({item.get('source', '?')}) [{item.get('polarity', '?')}]")
            print(f"    text: {item.get('text', '')}")
            if item.get("effect"):
                print(f"    effect: {item.get('effect', '')}")
            if item.get("moment"):
                print(f"    moment: {item.get('moment', '')}")
        record = edit.get("record", {}) or {}
        print("--- candidate experience record (full) ---")
        print(f"    id: {record.get('id', '')}")
        print(f"    title: {record.get('title', '')}")
        print(f"    body: {record.get('body', '')}")
        print(f"    sources: {', '.join(record.get('sources', []) or [])}")
        if record.get("clusterId"):
            print(f"    cluster: {record.get('clusterId', '')}")
        for item in record.get("evidence", []) or []:
            print(f"    - ({item.get('source', '?')}) {item.get('text', '')}")
        counterevidence = record.get("counterevidence") or edit.get("counterevidence") or "none observed"
        print(f"    counterevidence: {counterevidence}")
        implication = (
            record.get("compilerImplication")
            or edit.get("compilerImplication")
            or "compiler appends this record to the experience block."
        )
        print(f"    compilerImplication: {implication}")
        print("--- staged generated artifact (full) ---")
        print(edit.get("stagedArtifact", ""))
        print("--- staged diff per candidate (full) ---")
        print(edit.get("diff", ""))
        print(f"{'=' * 72}")
        while True:
            answer = input(f"{edit['id']} [accept/reject/skip]? ").strip().lower()
            if answer in ("accept", "a"):
                decisions[edit["id"]] = "accepted"
                break
            if answer in ("reject", "r"):
                decisions[edit["id"]] = "rejected"
                break
            if answer in ("skip", "s", ""):
                print(
                    f"{edit['id']} skip treated as rejected:"
                    " skip does not satisfy the required human decision"
                )
                decisions[edit["id"]] = "rejected"
                break
    return decisions


def apply(
    *,
    state_dir: Optional[Path] = None,
    experience_root: Optional[Path] = None,
    decisions: Optional[Dict[str, str]] = None,
    reject_reasons: Optional[Dict[str, str]] = None,
    dry_run: bool = False,
) -> Dict:
    """Apply gate: the sole writer of accepted experience records.

    Refuses a missing or unreviewed proposal. Acceptance atomically writes
    only the approved experience authored source + staged generated artifact;
    rejections are recorded in private state. Never deploys to Hermes and
    never patches SOUL.
    """
    resolved_state = state_dir or default_state_dir()
    proposal = read_proposal(resolved_state)
    if proposal.get("appliedAt"):
        raise RuntimeError(
            f"proposal {proposal.get('id', '?')} was already applied"
            f" ({proposal.get('appliedAt')}); run improve-run again for a fresh one"
        )
    edits = proposal.get("edits", [])
    if not edits:
        return {"accepted": [], "rejected": [], "written": [], "dry_run": dry_run}
    edit_ids = [edit["id"] for edit in edits]

    resolved = dict(decisions) if decisions else review_in_terminal(proposal)
    reasons = dict(reject_reasons or {})
    # Accept the CLI vector form "rejected:<reason>" as a decision value.
    for edit_id, verdict in list(resolved.items()):
        name, _, reason = verdict.partition(":")
        if reason:
            if name != "rejected" or reason not in REJECT_REASONS:
                raise RuntimeError(
                    f"bad decision {verdict!r} for {edit_id!r}"
                    f" (reasons: {', '.join(REJECT_REASONS)})"
                )
            resolved[edit_id] = name
            reasons.setdefault(edit_id, reason)
    for edit_id in resolved:
        if edit_id not in edit_ids:
            raise RuntimeError(
                f"decision names unknown edit {edit_id!r} (edits: {', '.join(edit_ids)})"
            )
    for edit_id in reasons:
        if edit_id not in edit_ids:
            raise RuntimeError(
                f"rejection reason names unknown edit {edit_id!r} (edits: {', '.join(edit_ids)})"
            )
    undecided = [edit_id for edit_id in edit_ids if edit_id not in resolved]
    if undecided:
        raise RuntimeError(
            f"proposal is unreviewed: no decision for {', '.join(undecided)}"
        )
    for edit_id, verdict in resolved.items():
        if verdict not in ("accepted", "rejected"):
            raise RuntimeError(f"bad verdict {verdict!r} for {edit_id!r}")

    root = experience_root or experience.experience_root()
    accepted = [e for e in edit_ids if resolved[e] == "accepted"]
    rejected = [e for e in edit_ids if resolved[e] == "rejected"]
    # Apply consumes only final annotated records: every edit must carry an
    # annotate verdict, and accepted edits must be annotation keeps with a
    # complete final record. Synth plans never reach here.
    for edit in edits:
        annotation = edit.get("annotation") or {}
        verdict = annotation.get("verdict")
        if verdict not in ("keep", "drop", "revert"):
            raise RuntimeError(
                f"edit {edit.get('id', '?')} has no final annotation;"
                " staged change plans cannot reach apply without annotate"
            )
        if resolved.get(edit["id"]) == "accepted" and verdict != "keep":
            raise RuntimeError(
                f"edit {edit.get('id', '?')} cannot be accepted"
                f" (annotation verdict is {verdict!r}, want 'keep')"
            )
        if resolved.get(edit["id"]) == "accepted":
            record = edit.get("record") or {}
            for field in ("id", "title", "body", "sources", "clusterId", "evidence", "counterevidence", "compilerImplication"):
                if not record.get(field):
                    raise RuntimeError(
                        f"edit {edit.get('id', '?')} annotation final record"
                        f" is missing {field}; annotation is the sole full-record origin"
                    )
    written: List[str] = []
    if not dry_run:
        for edit in edits:
            if resolved[edit["id"]] == "accepted":
                record = edit["record"]
                authored_target = experience.authored_dir(root) / f"{record['id']}.md"
                staged_target = experience.staged_dir(root) / f"{record['id']}.md"
                authored_backup = (
                    authored_target.read_bytes() if authored_target.exists() else None
                )
                staged_backup = (
                    staged_target.read_bytes() if staged_target.exists() else None
                )
                try:
                    authored_path = experience.write_authored_source(
                        root, record, edit, proposal.get("id", "?")
                    )
                    staged_path = experience.write_staged_artifact(
                        root, record["id"], edit["stagedArtifact"]
                    )
                except BaseException:
                    if authored_backup is not None:
                        authored_target.parent.mkdir(parents=True, exist_ok=True)
                        authored_target.write_bytes(authored_backup)
                    else:
                        try:
                            authored_target.unlink()
                        except OSError:
                            pass
                    if staged_backup is not None:
                        staged_target.parent.mkdir(parents=True, exist_ok=True)
                        staged_target.write_bytes(staged_backup)
                    else:
                        try:
                            staged_target.unlink()
                        except OSError:
                            pass
                    raise
                written.extend([str(authored_path), str(staged_path)])
            elif resolved[edit["id"]] == "rejected":
                record = edit.get("record", {}) or {}
                rejection = {
                    "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "proposal": proposal.get("id", "?"),
                    "edit": edit["id"],
                    "reason": reasons.get(edit["id"], "other"),
                    "title": record.get("title") or edit.get("title", ""),
                    "clusterId": record.get("clusterId", ""),
                    "recordId": record.get("id", ""),
                    "sources": list(record.get("sources", []) or []),
                }
                rejections_path = resolved_state / "rejections.jsonl"
                rejections_path.parent.mkdir(parents=True, exist_ok=True)
                with open(rejections_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(rejection) + "\n")
        proposal["reviewed"] = True
        proposal["appliedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        proposal["decisions"] = resolved
        tmp_path = resolved_state / "proposal.json.tmp"
        tmp_path.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp_path, resolved_state / "proposal.json")
    return {"accepted": accepted, "rejected": rejected, "written": written, "dry_run": dry_run}
