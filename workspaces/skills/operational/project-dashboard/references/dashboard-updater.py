#!/usr/bin/env python3
"""
Dashboard updater — scans git repos and CRM, regenerates auto-sections
in /data/projects/DASHBOARD.md.

Safe to run repeatedly. Only content between AUTO-START/AUTO-END markers
is replaced; manual notes and structure outside markers are preserved.

Designed for cron: produces no output unless something changed.
"""

import sqlite3
import subprocess
import re
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECTS_ROOT = Path("/data/projects")
DASHBOARD = PROJECTS_ROOT / "DASHBOARD.md"
CRM_DB = Path("/data/crm/crm.db")
NOW = datetime.now(timezone.utc)
CT_TZ = timezone(timedelta(hours=-5))  # Central Time

# ── Git helpers ──────────────────────────────────────────────────────────

def get_git_info(repo_path: Path) -> dict | None:
    """Return git metadata for a repo, or None if it's not a git repo."""
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%ci %s"],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            return None
        last_commit_raw = r.stdout.strip()
    except Exception:
        return None

    try:
        r = subprocess.run(
            ["git", "log", "--since=30 days ago", "--oneline"],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        commits_30d = len([l for l in r.stdout.strip().split("\n") if l])
    except Exception:
        commits_30d = 0

    try:
        r = subprocess.run(
            ["git", "log", "--since=7 days ago", "--oneline"],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        commits_7d = len([l for l in r.stdout.strip().split("\n") if l])
    except Exception:
        commits_7d = 0

    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        uncommitted = len([l for l in r.stdout.strip().split("\n") if l])
    except Exception:
        uncommitted = 0

    return {
        "last_commit": last_commit_raw,
        "commits_30d": commits_30d,
        "commits_7d": commits_7d,
        "uncommitted": uncommitted,
    }


def find_repos(root: Path) -> list[Path]:
    """Find all git repos under root (max depth 3)."""
    repos = []
    for gitdir in root.glob("*/.git"):
        repos.append(gitdir.parent)
    for gitdir in root.glob("*/*/.git"):
        repos.append(gitdir.parent)
    for gitdir in root.glob("*/*/*/.git"):
        repos.append(gitdir.parent)
    return sorted(repos)


def classify_project(info: dict) -> str:
    """Return status emoji based on commit recency."""
    if info["commits_7d"] > 0:
        return "active"      # 🔴
    if info["commits_30d"] > 0:
        return "semi"        # 🟡
    return "dormant"         # ⚫


# ── CRM helpers ──────────────────────────────────────────────────────────

def get_crm_deals() -> list[dict]:
    """Pull active and recent deals from CRM."""
    if not CRM_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(CRM_DB))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Active deals (not closed)
        cur.execute("""
            SELECT d.title, d.value, d.stage, d.tags,
                   c.name as contact_name, co.name as company_name
            FROM deals d
            LEFT JOIN contacts c ON c.id = json_extract(d.contacts, '$[0]')
            LEFT JOIN companies co ON co.id = d.company
            WHERE d.stage NOT IN ('closed-won', 'closed-lost')
            ORDER BY d.value DESC
        """)
        active = [dict(r) for r in cur.fetchall()]

        # Closed deals (recent — last 6 months)
        cur.execute("""
            SELECT d.title, d.value, d.stage,
                   c.name as contact_name, co.name as company_name
            FROM deals d
            LEFT JOIN contacts c ON c.id = json_extract(d.contacts, '$[0]')
            LEFT JOIN companies co ON co.id = d.company
            WHERE d.stage IN ('closed-won', 'closed-lost')
              AND d.updated_at > date('now', '-6 months')
            ORDER BY d.updated_at DESC
        """)
        closed = [dict(r) for r in cur.fetchall()]

        conn.close()
        return {"active": active, "closed": closed}
    except Exception:
        return {"active": [], "closed": []}


# ── Table builders ───────────────────────────────────────────────────────

def build_project_tables(repos: list[Path]) -> str:
    """Build the auto-generated project status tables."""
    rows_active = []
    rows_semi = []
    rows_dormant = []

    for repo in repos:
        rel = repo.relative_to(PROJECTS_ROOT)
        info = get_git_info(repo)
        if info is None:
            continue

        status = classify_project(info)

        if status == "active":
            rows_active.append(
                f"| {repo.name} | `{rel}` | {info['last_commit'][:10]} | "
                f"{info['commits_7d']} | {info['uncommitted']} | — | — |"
            )
        elif status == "semi":
            rows_semi.append(
                f"| {repo.name} | `{rel}` | {info['last_commit'][:10]} | "
                f"{info['commits_30d']} | {info['uncommitted']} | — | — |"
            )
        else:
            rows_dormant.append(
                f"| {repo.name} | `{rel}` | {info['last_commit'][:10]} | "
                f"{info['uncommitted']} |"
            )

    lines = []
    lines.append("## 🔴 Active (commits in last 7 days)\n")
    if rows_active:
        lines.append("| Project | Path | Last Commit | 7d Commits | Uncommitted | Blocker | Next Action |")
        lines.append("|---|---|---|---|---|---|---|")
        lines.extend(rows_active)
    else:
        lines.append("*No projects with commits in the last 7 days.*")
    lines.append("")

    lines.append("## 🟡 Semi-Active (commits in last 30 days, none in 7)\n")
    if rows_semi:
        lines.append("| Project | Path | Last Commit | 30d Commits | Uncommitted | Blocker | Next Action |")
        lines.append("|---|---|---|---|---|---|---|")
        lines.extend(rows_semi)
    else:
        lines.append("*No semi-active projects.*")
    lines.append("")

    lines.append("## ⚫ Dormant (no commits in 30+ days)\n")
    if rows_dormant:
        lines.append("| Project | Path | Last Commit | Uncommitted |")
        lines.append("|---|---|---|")
        lines.extend(rows_dormant)
    else:
        lines.append("*No dormant projects.*")

    return "\n".join(lines)


def build_deal_tables(deals: dict) -> str:
    """Build auto-generated CRM deal tables."""
    lines = []

    lines.append("## 💰 Active Deals (CRM)\n")
    active = deals.get("active", [])
    if active:
        lines.append("| Deal | Client | Value | Stage | Repo | Status |")
        lines.append("|---|---|---|---|---|---|")
        for d in active:
            client = d.get("contact_name") or d.get("company_name") or "—"
            value = f"${d['value']:,.0f}" if d.get("value") else "—"
            lines.append(f"| {d['title']} | {client} | {value} | {d['stage']} | — | — |")
    else:
        lines.append("*No active deals in CRM.*")
    lines.append("")

    lines.append("## ✅ Closed Deals\n")
    closed = deals.get("closed", [])
    if closed:
        lines.append("| Deal | Client | Value | Stage |")
        lines.append("|---|---|---|---|")
        for d in closed:
            client = d.get("contact_name") or d.get("company_name") or "—"
            value = f"${d['value']:,.0f}" if d.get("value") else "—"
            lines.append(f"| {d['title']} | {client} | {value} | {d['stage']} |")
    else:
        lines.append("*No recent closed deals.*")

    return "\n".join(lines)


# ── Dashboard patching ───────────────────────────────────────────────────

AUTO_PROJECTS_RE = re.compile(
    r"<!-- AUTO-START:PROJECTS -->.*?<!-- AUTO-END:PROJECTS -->", re.DOTALL
)
AUTO_DEALS_RE = re.compile(
    r"<!-- AUTO-START:DEALS -->.*?<!-- AUTO-END:DEALS -->", re.DOTALL
)
TIMESTAMP_RE = re.compile(
    r"> \*\*Last auto-refresh:\*\* .*"
)


def patch_dashboard(dashboard_path: Path, new_projects: str, new_deals: str):
    """Replace auto-sections in the dashboard file."""
    content = dashboard_path.read_text()

    now_ct = NOW.astimezone(CT_TZ).strftime("%Y-%m-%d %H:%M CT")

    # Update timestamp
    content = TIMESTAMP_RE.sub(
        f"> **Last auto-refresh:** {now_ct}",
        content,
    )

    # Replace project section
    replacement_p = f"<!-- AUTO-START:PROJECTS -->\n\n{new_projects}\n\n<!-- AUTO-END:PROJECTS -->"
    content = AUTO_PROJECTS_RE.sub(replacement_p, content)

    # Replace deals section
    replacement_d = f"<!-- AUTO-START:DEALS -->\n\n{new_deals}\n\n<!-- AUTO-END:DEALS -->"
    content = AUTO_DEALS_RE.sub(replacement_d, content)

    dashboard_path.write_text(content)


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    repos = find_repos(PROJECTS_ROOT)
    project_tables = build_project_tables(repos)
    deal_data = get_crm_deals()
    deal_tables = build_deal_tables(deal_data)

    if DASHBOARD.exists():
        old = DASHBOARD.read_text()
    else:
        old = ""

    patch_dashboard(DASHBOARD, project_tables, deal_tables)

    new = DASHBOARD.read_text()
    if new != old:
        # Only produce output when something changed (cron watchdog pattern)
        print("Dashboard updated.")
    else:
        # Silent — nothing changed
        pass


if __name__ == "__main__":
    main()
