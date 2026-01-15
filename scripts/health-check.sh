#!/bin/bash
# Health Check Agent - runs at 4am via cron (before job search)
# Checks posting URLs, looks for new roles at companies you've applied to
# See: scripts/health-check-prompt.md for full instructions

# Ensure HOME is set (cron may not set it)
export HOME="${HOME:-/home/illm}"

# Scripts directory (where this script and health-check-prompt.md live)
SCRIPTS_DIR="${JOB_SEARCH_SCRIPTS:-$HOME/job-search-agent/scripts}"

# Data directory (where config.yaml, postings/, digest/, etc. live)
# Can be separate from scripts (e.g., DATA_DIR=~/resume for private data)
DATA_DIR="${JOB_SEARCH_DATA:-$HOME/job-search-agent}"
cd "$DATA_DIR" || exit 1

# Ensure claude CLI is in PATH (cron uses minimal PATH)
export PATH="/home/illm/.local/bin:$PATH"

DATE=$(date +%Y-%m-%d)
LOGFILE="logs/health-check-${DATE}.log"

mkdir -p logs

exec >> "$LOGFILE" 2>&1

echo "=== Health Check Agent ==="
echo "Started: $(date -Iseconds)"
echo "Data dir: $DATA_DIR"
echo "Scripts dir: $SCRIPTS_DIR"

# Activate venv for Python tools (venv lives in scripts repo, not data dir)
REPO_ROOT="$(dirname "$SCRIPTS_DIR")"
if ! source "$REPO_ROOT/.venv/bin/activate" 2>&1; then
    echo "ERROR: Failed to activate venv from $REPO_ROOT/.venv"
fi

# Add Go bin to PATH for beads (bd)
export PATH="$PATH:$(go env GOPATH 2>/dev/null || echo "$HOME/go")/bin"

if ! claude -p "$(cat $SCRIPTS_DIR/health-check-prompt.md)" \
  --model opus \
  --allowedTools "WebFetch,Read,Write,Edit,Bash,Glob,Grep"; then
    echo "ERROR: Claude agent failed with exit code $?"
fi

echo "Finished: $(date -Iseconds)"
