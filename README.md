# Job Search Agent

Autonomous agent that runs daily at 5am to scan emails, collect job postings, and send a digest.

## Run

```bash
./scripts/daily-job-search.sh
```

Or with Docker:
```bash
docker compose run --rm agent daily
```

## Structure

```
├── config.yaml              # Preferences (roles, salary, sources)
├── credentials.json         # Gmail OAuth client
├── gmail-tokens-*.json      # Gmail access tokens
├── jb_resume_2025.tex       # Resume for keyword matching
├── linkedin_archive/        # Connections for referral detection
├── postings/                # Job applications (state machine)
├── digest/                  # Daily digests
└── scripts/
    ├── phase1-email.md      # Email scanning
    ├── phase2-jobs.md       # Job collection
    ├── phase3-digest.md     # Digest generation
    ├── phase4-improve.md    # Self-improvement
    └── daily-job-search.sh  # Entry point
```

## Cron

```bash
0 5 * * * cd ~/agentic-job-hunter && ./scripts/daily-job-search.sh
```
