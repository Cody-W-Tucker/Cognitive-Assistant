---
name: project-dashboard
description: Build and maintain auto-refreshing project health dashboards that aggregate git activity, CRM deal status, and manual notes into a single scanable view. Uses marker-delimited auto-sections with a watchdog cron pattern.
category: operational
---

## When to Use

When the user needs a bird's-eye view across all active projects — which ones have momentum, which are stalled, which have uncommitted work at risk, and which client deals need attention. Triggers on requests like "project status overview," "what's active right now," "dashboard for all my repos," "track blockers across projects," or "set up automated project tracking."

## Architecture

### Dashboard File

A single markdown file (typically at the project root, e.g. `/data/projects/DASHBOARD.md`) with three zones:

1. **Auto-generated sections** wrapped in `<!-- AUTO-START:NAME -->` / `<!-- AUTO-END:NAME -->` markers. These are machine-regenerated on each refresh. Separate markers per data source (e.g. `PROJECTS`, `DEALS`).
2. **Manual notes section** — hand-maintained by the user for blockers, context, and decisions. Lives outside the markers.
3. **Timestamp line** at the top showing last refresh time and cadence.

The update script replaces ONLY content between markers using regex (`re.DOTALL`). Manual notes outside markers survive every refresh.

### Git Activity Classification

Scan all git repos under the projects root (max depth 3 for nested/submodule repos). For each repo, run:

```
git log -1 --format='%ci %s'     → last commit
git log --since='7 days ago' --oneline   → count
git log --since='30 days ago' --oneline  → count
git status --porcelain                  → uncommitted count
```

Classification rules:

| Class | Rule | Emoji |
|---|---|---|
| Active | ≥1 commit in last 7 days | 🔴 |
| Semi-Active | ≥1 commit in last 30 days, none in 7 | 🟡 |
| Dormant | No commits in 30+ days | ⚫ |

Also surface **uncommitted files** as a risk signal (work that could be lost).

### CRM Integration

Pull deal status from the CRM SQLite database. Active deals: stage NOT IN (`closed-won`, `closed-lost`). Recently closed: last 6 months. Map deals to repos where a corresponding project directory exists.

CRM schema notes (SQLite with JSON columns):
- `deals.contacts` — JSON array of contact IDs, `json_extract(d.contacts, '$[0]')` for primary
- `deals.stage` — values include `qualified`, `closed-won`, `closed-lost`
- Deals link to contacts via JSON arrays, contacts link to companies

### Cron Pattern

Use `no_agent=true` with a watchdog script:

- **Script** runs, regenerates auto-sections, writes dashboard
- **Output**: "Dashboard updated." only when content actually changed (compare old vs new file)
- **Silent** (no delivery to user) when nothing changed — the watchdog pattern
- **Schedule**: weekly at start of business week (Monday 8 AM user-local time)

**Timezone conversion**: cron schedules are ALWAYS UTC. Convert user's local time:
- CT (Central): 8 AM CT = 13:00 UTC (CDT, UTC-5) or 14:00 UTC (CST, UTC-6)
- When in doubt, confirm the user's timezone and current offset

Create the cron job with:
```
cronjob(
  action='create',
  name='Project Dashboard Weekly Refresh',
  schedule='0 13 * * 1',    # Monday 8 AM CT
  script='dashboard-updater.py',
  no_agent=true,
  enabled_toolsets=['terminal'],
)
```

## Script Implementation

The update script ([`references/dashboard-updater.py`](references/dashboard-updater.py)) should:

1. **Find repos**: walk project root for `.git` directories at depth 1–3
2. **Gather git data**: `subprocess.run` for each repo, capture stdout, handle timeouts
3. **Query CRM**: `sqlite3.connect` to the CRM database, pull active and recent closed deals
4. **Classify**: apply 7d/30d rules per repo
5. **Build tables**: generate markdown tables for active, semi-active, dormant, deals
6. **Patch dashboard**: regex-replace content between markers, update timestamp
7. **Compare**: read old file, write new, output only if changed

Key implementation details:
- Use `re.DOTALL` for multi-line marker matching
- Timestamp regex: `r"> \*\*Last auto-refresh:\*\* .*"` — plain markdown, NOT HTML (no `</p>`)
- `subprocess.run` with `timeout=10` per git command to handle large/broken repos
- CRM database path may vary; check `/data/crm/crm.db` as default

## Pitfalls

- **Cron timezone trap**: Always convert user-local time to UTC. Never assume the cron scheduler uses local time.
- **Nested repos**: `find` with depth 3 catches submodules and nested `.git` dirs inside larger projects. This is usually desirable — surface them rather than hiding.
- **Timestamp regex**: Match plain markdown line endings, not HTML tags. `.md` files don't have `</p>`.
- **Don't regenerate the whole file**: Use markers. Without them, manual notes get clobbered every refresh.
- **CRM schema varies**: Contact linkage uses JSON arrays. Use `json_extract()` in SQLite, not direct column references.
- **Watchdog silence**: If the script produces no stdout, `no_agent=true` delivers nothing. This is the desired behavior for "no changes." Only produce output when the dashboard actually changed.

## Dashboards Deployed

| Dashboard | Location | Scope | Cron |
|---|---|---|---|
| Main Project Dashboard | `/data/projects/DASHBOARD.md` | 32 repos + CRM deals | Monday 8 AM CT (`07841130e223`) |
