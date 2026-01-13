#!/bin/bash
set -e

cd /home/agent/job-search

# Initialize beads if not already done
if [ ! -d ".beads" ]; then
    bd init 2>/dev/null || true
fi

case "$1" in
    daily)
        # Run all 4 phases sequentially
        echo "=== Daily Job Search Agent (Phased) ==="
        echo "Started: $(date -Iseconds)"

        # Clean up stale state
        rm -f /tmp/phase1-state.yaml /tmp/phase2-state.yaml /tmp/phase3-state.yaml /tmp/phase4-state.yaml

        echo ""
        echo "--- Phase 1: Email Scanning ---"
        claude -p "$(cat scripts/phase1-email.md)" \
            --model opus \
            --allowedTools "Read,Write,Bash,Glob,Grep" || true

        echo ""
        echo "--- Phase 2: Job Collection ---"
        claude -p "$(cat scripts/phase2-jobs.md)" \
            --model opus \
            --allowedTools "WebFetch,WebSearch,Read,Write,Edit,Bash,Glob,Grep" || true

        echo ""
        echo "--- Phase 3: Digest Generation ---"
        claude -p "$(cat scripts/phase3-digest.md)" \
            --model opus \
            --allowedTools "WebFetch,WebSearch,Read,Write,Edit,Bash,Glob,Grep" || true

        echo ""
        echo "--- Phase 4: Self-Improvement ---"
        claude -p "$(cat scripts/phase4-improve.md)" \
            --model opus \
            --allowedTools "Read,Write,Edit,Bash,Glob,Grep" || true

        echo ""
        echo "Finished: $(date -Iseconds)"
        ;;

    daily-legacy)
        # Run old single-session agent (for comparison/fallback)
        echo "=== Daily Job Search Agent (Legacy Single-Session) ==="
        echo "Started: $(date -Iseconds)"
        claude -p "$(cat scripts/daily-agent.md)" \
            --model opus \
            --allowedTools "WebFetch,WebSearch,Read,Write,Edit,Bash,Glob,Grep"
        echo "Finished: $(date -Iseconds)"
        ;;

    phase1)
        echo "=== Phase 1: Email Scanning ==="
        claude -p "$(cat scripts/phase1-email.md)" \
            --model opus \
            --allowedTools "Read,Write,Bash,Glob,Grep"
        ;;

    phase2)
        echo "=== Phase 2: Job Collection ==="
        claude -p "$(cat scripts/phase2-jobs.md)" \
            --model opus \
            --allowedTools "WebFetch,WebSearch,Read,Write,Edit,Bash,Glob,Grep"
        ;;

    phase3)
        echo "=== Phase 3: Digest Generation ==="
        claude -p "$(cat scripts/phase3-digest.md)" \
            --model opus \
            --allowedTools "WebFetch,WebSearch,Read,Write,Edit,Bash,Glob,Grep"
        ;;

    phase4)
        echo "=== Phase 4: Self-Improvement ==="
        claude -p "$(cat scripts/phase4-improve.md)" \
            --model opus \
            --allowedTools "Read,Write,Edit,Bash,Glob,Grep"
        ;;

    health)
        echo "=== Health Check Agent ==="
        echo "Started: $(date -Iseconds)"
        claude -p "$(cat scripts/health-check-prompt.md)" \
            --model opus \
            --allowedTools "WebFetch,Read,Write,Edit,Bash,Glob,Grep"
        echo "Finished: $(date -Iseconds)"
        ;;

    hourly)
        echo "=== Fresh Job Monitor (2-hour window) ==="
        echo "Started: $(date -Iseconds)"
        claude -p "$(cat scripts/hourly-monitor.md)" \
            --model opus \
            --allowedTools "WebFetch,WebSearch,Read,Write,Bash,Glob,Grep"
        echo "Finished: $(date -Iseconds)"
        ;;

    shell)
        exec /bin/bash
        ;;

    *)
        exec "$@"
        ;;
esac
