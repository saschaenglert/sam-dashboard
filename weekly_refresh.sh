#!/bin/bash
# weekly_refresh.sh — re-measures stats and pushes to GitHub so Pages redeploys.
# Called by launchd (com.sascha.sam-dashboard-refresh) every Sunday at 23:00.
#
# Logs: ~/Library/Logs/sam-agents/sam-dashboard-refresh.log
set -u

DASHBOARD_DIR="/Users/samgonzales/Library/CloudStorage/Dropbox/Claude/Sam/tools/sam-dashboard"
LOG_DIR="$HOME/Library/Logs/sam-agents"
LOG_FILE="$LOG_DIR/sam-dashboard-refresh.log"

mkdir -p "$LOG_DIR"

# Append mode with timestamps
exec >> "$LOG_FILE" 2>&1
echo ""
echo "=== $(date '+%Y-%m-%d %H:%M:%S') starting refresh ==="

cd "$DASHBOARD_DIR" || { echo "cd failed"; exit 1; }

# 1. Regenerate index.html + last_stats.json from live repos
/opt/homebrew/bin/python3 update_stats.py || { echo "update_stats.py failed"; exit 1; }

# 2. If nothing changed, stop (GitHub Pages stays as-is)
if git diff --quiet index.html last_stats.json; then
  echo "no stat changes — nothing to push"
  exit 0
fi

# 3. Commit + push. Use per-invocation author so no global git config is needed.
git -c user.name="Sascha Englert" -c user.email="sascha.englert@web.de" \
    add index.html last_stats.json
git -c user.name="Sascha Englert" -c user.email="sascha.englert@web.de" \
    commit -m "weekly stats refresh $(date '+%Y-%m-%d')" || { echo "commit failed"; exit 1; }

# Push uses the gh auth'd credentials of the logged-in shell user
git push origin main || { echo "push failed"; exit 1; }

echo "pushed — Pages will redeploy shortly"
