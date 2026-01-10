#!/bin/bash
# Run the job search agent in Docker
# Usage: docker-run.sh [daily|health]
#
# Environment variables:
#   ANTHROPIC_API_KEY - Required
#   JOB_SEARCH_DATA   - Path to your data directory (default: ../data)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
MODE="${1:-daily}"

cd "$REPO_DIR"

# Validate
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY not set"
    exit 1
fi

if [ ! -d "${JOB_SEARCH_DATA:-./data}" ]; then
    echo "ERROR: Data directory not found: ${JOB_SEARCH_DATA:-./data}"
    echo "Create it with: mkdir -p data && cp config.template.yaml data/config.yaml"
    exit 1
fi

# Run
echo "Running $MODE agent in Docker..."
docker compose run --rm agent "$MODE" 2>&1 | tee -a "${JOB_SEARCH_DATA:-./data}/logs/docker-${MODE}-$(date +%Y-%m-%d).log"
