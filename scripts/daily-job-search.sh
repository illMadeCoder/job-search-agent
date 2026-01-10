#!/bin/bash
# Daily Job Search Agent - runs at 5am via cron
# See: scripts/daily-agent.md for full instructions

# Change to your repo directory (update this path)
REPO_DIR="${JOB_SEARCH_REPO:-$HOME/agentic-job-hunter}"
cd "$REPO_DIR" || exit 1

DATE=$(date +%Y-%m-%d)
LOGFILE="logs/daily-agent-${DATE}.log"

mkdir -p logs

exec >> "$LOGFILE" 2>&1

echo "=== Daily Job Search Agent ==="
echo "Started: $(date -Iseconds)"

# Activate venv for Gmail access
if ! source .venv/bin/activate 2>&1; then
    echo "ERROR: Failed to activate venv"
fi

# Add Go bin to PATH for beads (bd)
export PATH="$PATH:$(go env GOPATH 2>/dev/null || echo "$HOME/go")/bin"

if ! claude -p "$(cat scripts/daily-agent.md)" \
  --allowedTools "WebFetch,WebSearch,Read,Write,Edit,Bash,Glob,Grep"; then
    echo "ERROR: Claude agent failed with exit code $?"
fi

echo "Finished: $(date -Iseconds)"
