#!/bin/bash
# Fresh Job Monitor - runs every 2 hours via cron
# Finds jobs posted in the last 2 hours and sends instant alerts
#
# Skips: Email scanning, Full digest, Self-improvement
# Does: Fresh job discovery + instant notification for brand new postings
#
# Schedule: Every 2 hours, 6am-10pm EST
# Quiet hours: 10pm-6am EST (no runs, no notifications)
#
# Usage: ./scripts/hourly-monitor.sh
# Docker: docker compose run --rm agent hourly

# Ensure HOME is set (cron may not set it)
export HOME="${HOME:-/home/illm}"

# Scripts directory (where this script and hourly-monitor.md live)
SCRIPTS_DIR="${JOB_SEARCH_SCRIPTS:-$HOME/job-search-agent/scripts}"

# Data directory (where config.yaml, postings/, digest/, etc. live)
# Can be separate from scripts (e.g., DATA_DIR=~/resume for private data)
DATA_DIR="${JOB_SEARCH_DATA:-$HOME/job-search-agent}"
cd "$DATA_DIR" || exit 1

# Ensure claude CLI and other tools are in PATH (cron uses minimal PATH)
export PATH="/home/illm/.local/bin:$PATH"

# Check quiet hours (10pm-6am EST)
HOUR_EST=$(TZ="America/New_York" date +%H)
if [ "$HOUR_EST" -ge 22 ] || [ "$HOUR_EST" -lt 6 ]; then
    echo "Quiet hours (10pm-6am EST) - skipping. Current EST hour: $HOUR_EST"
    exit 0
fi

# Also skip during daily agent window (5am EST)
if [ "$HOUR_EST" -eq 5 ]; then
    echo "Daily agent window (5am EST) - skipping to avoid conflict"
    exit 0
fi

TIMESTAMP=$(date +%Y-%m-%dT%H%M)
LOG_FILE="logs/hourly-monitor-${TIMESTAMP}.log"

# Create log directory if needed
mkdir -p logs

# Clean up logs older than 7 days (more aggressive than daily)
find logs -name "hourly-monitor-*.log" -mtime +7 -delete 2>/dev/null || true

# Start logging
exec > >(tee -a "$LOG_FILE") 2>&1

echo "════════════════════════════════════════════════════════════"
echo " HOURLY JOB MONITOR"
echo " Started: $(date -Iseconds)"
echo " Log: $LOG_FILE"
echo "════════════════════════════════════════════════════════════"

# Activate venv for Gmail access (venv lives in scripts repo, not data dir)
REPO_ROOT="$(dirname "$SCRIPTS_DIR")"
if ! source "$REPO_ROOT/.venv/bin/activate" 2>&1; then
    echo "WARNING: Failed to activate venv from $REPO_ROOT/.venv"
fi

# Clean up stale state
rm -f /tmp/hourly-monitor-state.yaml

# Run the fresh job monitor agent
if claude -p "$(cat $SCRIPTS_DIR/hourly-monitor.md)" \
  --model opus \
  --allowedTools "WebFetch,WebSearch,Read,Write,Bash,Glob,Grep" 2>&1; then
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo " HOURLY MONITOR COMPLETE"
    echo " Finished: $(date -Iseconds)"
    echo "════════════════════════════════════════════════════════════"
else
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo " HOURLY MONITOR FAILED (exit code $?)"
    echo " Finished: $(date -Iseconds)"
    echo "════════════════════════════════════════════════════════════"
    exit 1
fi
