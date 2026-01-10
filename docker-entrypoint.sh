#!/bin/bash
set -e

cd /home/agent/job-search

# Initialize beads if not already done
if [ ! -d ".beads" ]; then
    bd init 2>/dev/null || true
fi

case "$1" in
    daily)
        echo "=== Daily Job Search Agent ==="
        echo "Started: $(date -Iseconds)"
        claude -p "$(cat scripts/daily-agent.md)" \
            --allowedTools "WebFetch,WebSearch,Read,Write,Edit,Bash,Glob,Grep"
        echo "Finished: $(date -Iseconds)"
        ;;
    health)
        echo "=== Health Check Agent ==="
        echo "Started: $(date -Iseconds)"
        claude -p "$(cat scripts/health-check-prompt.md)" \
            --allowedTools "WebFetch,Read,Write,Edit,Bash,Glob,Grep"
        echo "Finished: $(date -Iseconds)"
        ;;
    shell)
        exec /bin/bash
        ;;
    *)
        exec "$@"
        ;;
esac
