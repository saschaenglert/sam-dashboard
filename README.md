# sam-dashboard

Public dashboard at `saschaenglert.github.io/sam-dashboard` — shows code + agent
stats across Sam's ecosystem. Updates weekly.

## Layout

```
sam-dashboard/
├── template.html        # HTML with {{PLACEHOLDERS}}
├── update_stats.py      # measures repos, fills template, writes index.html
├── index.html           # generated output (committed, served by Pages)
├── sam-avatar.jpg       # hero portrait
├── last_stats.json      # latest measured stats (debug)
├── build_template.py    # one-off: build template.html from a prototype
├── README.md
└── .gitignore
```

## Manual commands

```bash
# Regenerate index.html with current numbers
python3 update_stats.py

# See the stats without writing files
python3 update_stats.py --dry-run
```

## Weekly auto-refresh

Scheduled via launchd (plist in `~/Library/LaunchAgents/`). Every Sunday night:

1. Run `update_stats.py` — reads all Sam repos (immo, fewo, buchhaltung,
   hausverwalter, plattform/plugins), re-measures LOC / commits / transcripts /
   drafts, regenerates `index.html`.
2. `git add index.html last_stats.json && git commit -m "weekly stats refresh"`
3. `git push origin main`
4. GitHub Pages auto-deploys in ~1 minute.

## Data sources

| Stat | Source |
|------|--------|
| Per-tool LOC (frontend/backend/tests) | `wc -l` across `.py`, `.html`, `.js`, `.css` under `tools/<tool>/` |
| Per-tool commits | `git rev-list --count HEAD` in each tool repo |
| Shared platform LOC | `.py` files under `plattform/` |
| Transcripts indexed | `find orga/agents/youtube-agent/transcripts -name '*.md'` |
| LinkedIn drafts | `ls orga/agents/linkedin-agent/drafts/{new,archived}/*.md` |
| Knowledge entries | `wissen_api.py count` (falls back to `400+` if unavailable) |
| Quality gates, coverage min, scheduled jobs | Static constants at top of `update_stats.py` |

## Adding a new tool

Edit `TOOL_REPOS` in `update_stats.py`. Run `update_stats.py` — new tool's
numbers appear if a corresponding tool card exists in `template.html`.
Add the tool card manually first (copy an existing one in `template.html`).

## Known quirks

1. **Knowledge count is a static fallback** unless `wissen_api.py count`
   exists. Currently shows `400+`.
2. **Hausverwalter is hardcoded as "in dev"** — see `tools_status` in
   `update_stats.py`. Change when it goes live.
3. **Scheduled-jobs count is hardcoded** (currently 7). Update when agents
   change.
4. **Template placeholders must match** — if `update_stats.py` writes a value
   with no matching `{{KEY}}` in `template.html`, the script logs a warning
   but still runs.
5. **Nothing in GitHub Pages watches the repo automatically** — the weekly
   launchd job is what triggers the refresh. If launchd is disabled, numbers
   go stale.

## Deployment

GitHub Pages, source = `main` branch, root folder. No build step. Custom
domain can be added in repo Settings > Pages.
