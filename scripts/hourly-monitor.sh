#!/bin/bash
# Hourly Job Monitor - runs every hour via cron
# Lightweight job search that sends instant alerts for hot opportunities
#
# Skips: Email scanning, Full digest, Self-improvement
# Does: Job collection + instant notification for hot matches (score >= 60)
#
# Quiet hours: 10pm-6am EST (no runs, no notifications)
#
# Usage: ./scripts/hourly-monitor.sh
# Docker: docker compose run --rm agent hourly

REPO_DIR="${JOB_SEARCH_REPO:-$HOME/agentic-job-hunter}"
cd "$REPO_DIR" || exit 1

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

# Activate venv for Gmail access
if ! source .venv/bin/activate 2>&1; then
    echo "WARNING: Failed to activate venv"
fi

# Clean up stale state
rm -f /tmp/hourly-monitor-state.yaml

# Run the lightweight agent
if claude -p "$(cat scripts/hourly-monitor.md)" \
  --model opus \
  --allowedTools "WebSearch,Read,Write,Bash,Glob,Grep" 2>&1; then
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
