#!/bin/bash
# Health Check Agent - runs at 4am via cron (before job search)
# Checks posting URLs, looks for new roles at companies you've applied to
# See: scripts/health-check-prompt.md for full instructions

cd /home/illm/resume

DATE=$(date +%Y-%m-%d)
LOGFILE="logs/health-check-${DATE}.log"

mkdir -p logs

exec >> "$LOGFILE" 2>&1

echo "=== Health Check Agent ==="
echo "Started: $(date -Iseconds)"

# Activate venv for Python tools
if ! source .venv/bin/activate 2>&1; then
    echo "ERROR: Failed to activate venv"
fi

# Add Go bin to PATH for beads (bd)
export PATH="$PATH:/home/illm/go/bin"

if ! claude -p "$(cat scripts/health-check-prompt.md)" \
  --allowedTools "WebFetch,Read,Write,Edit,Bash,Glob,Grep"; then
    echo "ERROR: Claude agent failed with exit code $?"
fi

echo "Finished: $(date -Iseconds)"
