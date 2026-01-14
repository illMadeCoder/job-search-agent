#!/bin/bash
# Daily Job Search Agent - runs at 5am via cron
# Executes 4 phases sequentially with state handoff between sessions
#
# Phase 1: Email Scanning (Opus)
# Phase 2: Job Collection (Opus)
# Phase 3: Digest Generation (Opus)
# Phase 4: Self-Improvement (Opus)
#
# Logs: Each phase gets its own log file in logs/phases/
# Retention: 30 days

# Don't use set -e - bash arithmetic ((x++)) returns 1 when x starts at 0
# We handle errors explicitly per-phase

# Ensure HOME is set (cron may not set it)
export HOME="${HOME:-/home/illm}"

# Change to your repo directory
REPO_DIR="${JOB_SEARCH_REPO:-$HOME/job-search-agent}"
cd "$REPO_DIR" || exit 1

# Ensure claude CLI and other tools are in PATH (cron uses minimal PATH)
export PATH="/home/illm/.local/bin:$PATH"

DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%dT%H%M)

# Create log directories
mkdir -p logs/phases

# Main log (summary only)
MAIN_LOG="logs/daily-agent-${DATE}.log"

# Per-phase logs
PHASE1_LOG="logs/phases/phase1-email-${TIMESTAMP}.log"
PHASE2_LOG="logs/phases/phase2-jobs-${TIMESTAMP}.log"
PHASE3_LOG="logs/phases/phase3-digest-${TIMESTAMP}.log"
PHASE4_LOG="logs/phases/phase4-improve-${TIMESTAMP}.log"

# Clean up logs older than 30 days
find logs/phases -name "*.log" -mtime +30 -delete 2>/dev/null || true

# Start main log
exec > >(tee -a "$MAIN_LOG") 2>&1

echo "════════════════════════════════════════════════════════════"
echo " DAILY JOB SEARCH AGENT"
echo " Started: $(date -Iseconds)"
echo " Logs: logs/phases/phase*-${TIMESTAMP}.log"
echo "════════════════════════════════════════════════════════════"

# Activate venv for Gmail access
if ! source .venv/bin/activate 2>&1; then
    echo "WARNING: Failed to activate venv"
fi

# Add Go bin to PATH for beads (bd)
export PATH="$PATH:$(go env GOPATH 2>/dev/null || echo "$HOME/go")/bin"

# Clean up any stale state files
rm -f /tmp/phase1-state.yaml /tmp/phase2-state.yaml /tmp/phase3-state.yaml /tmp/phase4-state.yaml

# Track overall success
PHASES_PASSED=0
PHASES_FAILED=0

# ──────────────────────────────────────────────────────────────
# PHASE 1: Email Scanning
# ──────────────────────────────────────────────────────────────
echo ""
echo "┌──────────────────────────────────────────────────────────┐"
echo "│ PHASE 1: Email Scanning                                  │"
echo "│ Log: $PHASE1_LOG"
echo "└──────────────────────────────────────────────────────────┘"
PHASE1_START=$(date -Iseconds)
echo "Started: $PHASE1_START"

if claude -p "$(cat scripts/phase1-email.md)" \
  --model opus \
  --allowedTools "Read,Write,Bash,Glob,Grep" 2>&1 | tee "$PHASE1_LOG"; then
    echo "Phase 1: SUCCESS"
    ((PHASES_PASSED++))
else
    echo "Phase 1: FAILED (exit code $?)"
    ((PHASES_FAILED++))
    # Create minimal state so phase 2 can continue
    cat > /tmp/phase1-state.yaml << 'EOF'
phase: email_scan
generated_at: null
emails_processed: 0
classified: {}
unclassified: []
stats:
  total_fetched: 0
  error: "Phase 1 failed"
EOF
fi

echo "Finished: $(date -Iseconds)"

# ──────────────────────────────────────────────────────────────
# PHASE 2: Job Collection
# ──────────────────────────────────────────────────────────────
echo ""
echo "┌──────────────────────────────────────────────────────────┐"
echo "│ PHASE 2: Job Collection                                  │"
echo "│ Log: $PHASE2_LOG"
echo "└──────────────────────────────────────────────────────────┘"
PHASE2_START=$(date -Iseconds)
echo "Started: $PHASE2_START"

if claude -p "$(cat scripts/phase2-jobs.md)" \
  --model opus \
  --allowedTools "WebFetch,WebSearch,Read,Write,Edit,Bash,Glob,Grep" 2>&1 | tee "$PHASE2_LOG"; then
    echo "Phase 2: SUCCESS"
    ((PHASES_PASSED++))
else
    echo "Phase 2: FAILED (exit code $?)"
    ((PHASES_FAILED++))
    # Create minimal state so phase 3 can continue
    cat > /tmp/phase2-state.yaml << 'EOF'
phase: job_collection
generated_at: null
emails_processed: {}
health_check: {}
collection:
  sources_attempted: 0
  error: "Phase 2 failed"
new_postings: []
errors:
  - phase: job_collection
    error: "Phase 2 agent failed"
EOF
fi

echo "Finished: $(date -Iseconds)"

# ──────────────────────────────────────────────────────────────
# PHASE 3: Digest Generation
# ──────────────────────────────────────────────────────────────
echo ""
echo "┌──────────────────────────────────────────────────────────┐"
echo "│ PHASE 3: Digest Generation                               │"
echo "│ Log: $PHASE3_LOG"
echo "└──────────────────────────────────────────────────────────┘"
PHASE3_START=$(date -Iseconds)
echo "Started: $PHASE3_START"

if claude -p "$(cat scripts/phase3-digest.md)" \
  --model opus \
  --allowedTools "WebFetch,WebSearch,Read,Write,Edit,Bash,Glob,Grep" 2>&1 | tee "$PHASE3_LOG"; then
    echo "Phase 3: SUCCESS"
    ((PHASES_PASSED++))
else
    echo "Phase 3: FAILED (exit code $?)"
    ((PHASES_FAILED++))
fi

echo "Finished: $(date -Iseconds)"

# ──────────────────────────────────────────────────────────────
# PHASE 4: Self-Improvement
# ──────────────────────────────────────────────────────────────
echo ""
echo "┌──────────────────────────────────────────────────────────┐"
echo "│ PHASE 4: Self-Improvement                                │"
echo "│ Log: $PHASE4_LOG"
echo "└──────────────────────────────────────────────────────────┘"
PHASE4_START=$(date -Iseconds)
echo "Started: $PHASE4_START"

if claude -p "$(cat scripts/phase4-improve.md)" \
  --model opus \
  --allowedTools "Read,Write,Edit,Bash,Glob,Grep" 2>&1 | tee "$PHASE4_LOG"; then
    echo "Phase 4: SUCCESS"
    ((PHASES_PASSED++))
else
    echo "Phase 4: FAILED (exit code $?)"
    ((PHASES_FAILED++))
fi

echo "Finished: $(date -Iseconds)"

# ──────────────────────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════"
echo " DAILY AGENT COMPLETE"
echo " Finished: $(date -Iseconds)"
echo " Phases passed: ${PHASES_PASSED}/4"
echo " Phases failed: ${PHASES_FAILED}/4"
echo ""
echo " Phase logs:"
echo "   $PHASE1_LOG"
echo "   $PHASE2_LOG"
echo "   $PHASE3_LOG"
echo "   $PHASE4_LOG"
echo "════════════════════════════════════════════════════════════"

# Exit with error if any phase failed
if [ $PHASES_FAILED -gt 0 ]; then
    exit 1
fi
