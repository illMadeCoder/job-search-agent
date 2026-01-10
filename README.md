# Autonomous Job Search Agent

A fully autonomous job search system powered by Claude that runs daily to scan emails, collect postings, track applications, and generate prioritized action items.

## Why?

Job searching is tedious. This system automates the grind:
- **5am daily**: Agent wakes up, scans your Gmail, checks job boards, updates your pipeline
- **You wake up**: Read a prioritized digest of what needs attention
- **Focus on what matters**: Interviews, networking, skill-building - not refreshing job boards

## Features

- **Gmail Integration** - Detects recruiter outreach, interview invites, offers, rejections
- **Multi-Source Collection** - Greenhouse, Lever, RemoteOK APIs + Google search
- **LinkedIn Data** - Connections for referrals, message history for ROI tracking
- **Smart Matching** - ATS keyword analysis, salary filtering, duplicate detection
- **State Management** - Track applications through full lifecycle with events
- **Trend Analysis** - Know which skills are rising/falling in demand
- **Daily Learning** - Surfaces one career advice article per day

## Architecture

```
4am  ─── Health Check ───► Verify posting URLs, find new roles
              │
5am  ─── Daily Agent ────► Scan Gmail
              │            Collect postings
              │            Analyze trends
              │            Generate digest
              ▼
You  ─── Read Digest ────► Prioritized actions for the day
```

## Tech Stack

- **Claude** - Autonomous agent (via claude-code CLI)
- **Beads** - Persistent task state across context windows
- **Gmail API** - OAuth2 for autonomous email access
- **Python** - LinkedIn/Gmail tooling
- **YAML** - Schema-driven data format

## Quick Start

```bash
# Clone
git clone https://github.com/yourusername/job-search-agent
cd job-search-agent

# Setup Python
python3 -m venv .venv
source .venv/bin/activate
pip install google-auth google-auth-oauthlib google-api-python-client

# Setup Beads
go install github.com/steveyegge/beads/cmd/bd@latest
bd init

# Gmail OAuth (one-time browser auth)
# 1. Create Google Cloud project, enable Gmail API
# 2. Download OAuth credentials to credentials.json
python scripts/gmail-auth.py

# Export LinkedIn data
# LinkedIn → Settings → Data Privacy → Get a copy
# Extract to linkedin_archive/

# Run manually
./scripts/daily-job-search.sh

# Or schedule with cron
0 4 * * * /path/to/scripts/health-check.sh
0 5 * * * /path/to/scripts/daily-job-search.sh
```

## Directory Structure

```
├── CLAUDE.md                 # Agent context and strategy
├── AGENTS.md                 # Beads landing-the-plane instructions
├── gmail-integration.md      # Gmail API setup guide
├── sources.yaml              # Job source configuration
├── postings/
│   ├── _schema.yaml          # Posting data format (v1)
│   └── _template.yaml        # Empty posting template
├── digest/
│   ├── _schema.yaml          # Digest format
│   └── _template.yaml        # Empty digest template
└── scripts/
    ├── daily-agent.md        # Full agent instructions
    ├── daily-job-search.sh   # 5am cron wrapper
    ├── health-check.sh       # 4am cron wrapper
    ├── health-check-prompt.md
    ├── gmail-auth.py         # OAuth setup
    ├── gmail-fetch.py        # Email fetching utility
    └── linkedin-tools.py     # LinkedIn data processing
```

## The Digest

Your morning briefing, prioritized:

1. **URGENT** - Offers expiring, interviews today
2. **HOT** - Best opportunities (match + referral + salary)
3. **PIPELINE ALERTS** - Stale apps, posting issues
4. **OUTREACH** - People to message
5. **PREP** - Upcoming interviews
6. **TRENDS** - Rising/falling skills
7. **INSIGHTS** - Your stats, skills gap

## Application Lifecycle

```
pending_review → applied → interviewing → offer
                    │            │           │
                    └── expired  └── rejected └── withdrawn
```

Each state change is an event in the audit log.

## Beads Integration

[Beads](https://github.com/steveyegge/beads) provides persistent memory across context windows:

```bash
bd ready                    # What needs attention
bd create "Follow up" -p 2  # Create task
bd close {id}               # Complete task
```

Tasks like "follow up in 7 days" survive agent restarts.

## Privacy

The `.gitignore` protects:
- `linkedin_archive/` - Your connections, messages
- `gmail-tokens*.json` - OAuth credentials
- `postings/*/` - Your actual applications
- `digest/*.yaml` - Your daily digests
- `logs/` - Agent run logs

Only schemas and scripts are public.

## License

MIT

---

Built with Claude Code and too much coffee.
