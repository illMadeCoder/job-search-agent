# Job Search Agent System

## Overview

An autonomous job search system powered by Claude that runs daily at 5am to:
- Scan Gmail for recruiter outreach, interview invites, offers, rejections
- Check job posting URLs are still active
- Collect new postings from accessible sources
- Analyze market trends and skills gaps
- Generate a prioritized daily digest

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     4am: Health Check                        │
│  • Verify posting URLs still active                          │
│  • Search for new roles at applied companies                 │
│  • Flag issues with .review suffix                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     5am: Daily Agent                         │
├─────────────────────────────────────────────────────────────┤
│  Phase 0: Scan Gmail                                         │
│    • Recruiter outreach → create posting                     │
│    • Interview invites → add event                           │
│    • Rejections → update state                               │
├─────────────────────────────────────────────────────────────┤
│  Phase 1: Update Existing Postings                           │
│    • Check expirations (30 days)                             │
│    • Process beads tasks                                     │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: Collect New Postings                               │
│    • API sources (Greenhouse, Lever, RemoteOK)               │
│    • Search sources (Google site:)                           │
│    • Check LinkedIn connections for referrals                │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: Generate Digest                                    │
│    • Urgent items (offers, interviews today)                 │
│    • Hot opportunities (high match + referral)               │
│    • Pipeline alerts                                         │
│    • Market trends                                           │
│    • Daily learning article                                  │
└─────────────────────────────────────────────────────────────┘
```

## Two-Tier Strategy

### Practice Tier (Apply Now)
- General tech companies, startups
- Goal: Interview reps, market calibration, potential offer

### Reserved Tier (Save for Later)
- Companies in your target industry (healthcare, fintech, etc.)
- Companies you genuinely want to work at

**Rule**: Don't burn bridges at reserved tier companies during practice.

---

## Posting File Naming

```
postings/{company}.{role}.{state}.{YYYY-MM-DDTHHMM}Z.yaml
```

Each posting is a single YAML file (not a folder).

### States

| State | Meaning |
|-------|---------|
| `pending_review` | Agent created, waiting for you to act |
| `applied` | Submitted, waiting (30-day expiry) |
| `interviewing` | In interview process |
| `offer` | Received offer (terminal) |
| `rejected` | Explicit rejection (terminal) |
| `expired` | 30 days no response (terminal) |
| `withdrawn` | You pulled out (terminal) |

### Review Flag

`.review` segment in filename = needs attention (posting missing OR new roles found)

---

## Data Format

**Philosophy: Materialized View**
- Top-level fields = current state (easy to query)
- Events = audit log (how we got here)
- Derived fields computed on read (not stored)

See `postings/_schema.yaml` for full reference.

### Event Types

| Type | When | Key Data |
|------|------|----------|
| `created` | File created | source, posting_status |
| `recruiter_inbound` | Recruiter contacted you | channel, message_snippet |
| `health_check` | Daily check | posting_status, new_roles_found |
| `applied` | Submitted app | method, referrer, resume_version |
| `interview_scheduled` | Interview set | round, date, format, interviewers |
| `interview_completed` | After interview | questions, topics, vibe |
| `offer_received` | Got offer | base, bonus, equity, deadline |
| `rejection` | Rejected | stage, reason, feedback |
| `expired` | 30 days silence | days_waited |
| `withdrawn` | You pulled out | reason, stage |

---

## Daily Automation

### Configuration

Scripts support separate data and script directories via environment variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `JOB_SEARCH_DATA` | Where config.yaml, postings/, digest/ live | `~/job-search-agent` |
| `JOB_SEARCH_SCRIPTS` | Where scripts/*.sh and *.md live | `~/job-search-agent/scripts` |

**Typical setup for private data**:
```bash
# Put private data in ~/resume, scripts in ~/job-search-agent
export JOB_SEARCH_DATA="$HOME/resume"
export JOB_SEARCH_SCRIPTS="$HOME/job-search-agent/scripts"
```

### Cron Schedule

```bash
# Option 1: All data in job-search-agent (default)
0 4 * * * cd ~/job-search-agent && ./scripts/health-check.sh
0 5 * * * cd ~/job-search-agent && ./scripts/daily-job-search.sh

# Option 2: Private data in ~/resume, scripts in job-search-agent
0 4 * * * JOB_SEARCH_DATA=$HOME/resume ~/job-search-agent/scripts/health-check.sh
0 5 * * * JOB_SEARCH_DATA=$HOME/resume ~/job-search-agent/scripts/daily-job-search.sh
```

---

## Agent State (Beads)

Uses [beads](https://github.com/steveyegge/beads) for task persistence across context windows.

| System | Purpose |
|--------|---------|
| `postings/*.yaml` | Job data, events (human review) |
| `digest/*.yaml` | Daily summary (human review) |
| **Beads** | Agent task queue (internal) |

**Key commands**:
```bash
bd ready              # What needs attention now
bd create "task" -p 1 # Create priority-1 task
bd close {id}         # Mark complete
bd sync               # Persist to git
```

---

## Integrations

### Gmail API
- OAuth2 with refresh token for autonomous access
- Scans for recruiter outreach, interview invites, offers, rejections
- See `gmail-integration.md`

### LinkedIn Archive
- Weekly refresh of data export
- Connections for referral matching
- Messages for recruiter outreach history
- Past applications to avoid re-applying

---

## Your Daily Workflow

**Morning (10-15 min)** - Work through the digest:

1. **URGENT** - Expiring offers, interviews today
2. **HOT** - Best opportunities ranked by score
3. **OUTREACH** - Referrals to contact, follow-ups
4. **MANUAL HUNT** - Browse LinkedIn/Indeed (agent can't)
5. **PIPELINE ALERTS** - Stale applications, posting issues
6. **PREP** - Upcoming interviews

---

## Required Setup

1. Gmail OAuth credentials (`credentials.json`)
2. LinkedIn data export (`linkedin_archive/`)
3. Beads installed (`go install github.com/steveyegge/beads/cmd/bd@latest`)
4. Python venv with Google API libraries
