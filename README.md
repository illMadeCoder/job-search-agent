# Autonomous Job Search Agent

A fully autonomous job search system powered by Claude that runs daily to scan emails, collect postings, track applications, and generate prioritized action items.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              YOUR INPUTS                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  CLAUDE.md          sources.yaml        linkedin_archive/    Gmail OAuth    │
│  ┌──────────┐       ┌──────────┐        ┌──────────┐        ┌──────────┐   │
│  │• Roles   │       │• Company │        │• Connec- │        │• Token   │   │
│  │• Salary  │       │  APIs    │        │  tions   │        │  refresh │   │
│  │• Location│       │• Keywords│        │• Messages│        │          │   │
│  └────┬─────┘       └────┬─────┘        └────┬─────┘        └────┬─────┘   │
└───────┼──────────────────┼───────────────────┼───────────────────┼─────────┘
        │                  │                   │                   │
        └──────────────────┴─────────┬─────────┴───────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DAILY AUTOMATION                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  4am ┌─────────────┐     5am ┌─────────────────────────────────────────┐    │
│      │ Health      │         │ Daily Agent                             │    │
│      │ Check       │────────▶│                                         │    │
│      │             │         │  ┌─────────┐  ┌─────────┐  ┌─────────┐ │    │
│      │ • URL check │         │  │ Scan    │  │ Collect │  │ Analyze │ │    │
│      │ • New roles │         │  │ Gmail   │─▶│ Jobs    │─▶│ Trends  │ │    │
│      │ • Flag .rev │         │  └─────────┘  └─────────┘  └─────────┘ │    │
│      └─────────────┘         └──────────────────┬──────────────────────┘    │
│                                                 │                            │
└─────────────────────────────────────────────────┼────────────────────────────┘
                                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              YOUR OUTPUTS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  digest/2024-01-15.yaml              postings/{company}.{state}/             │
│  ┌────────────────────────┐          ┌────────────────────────┐             │
│  │ 1. URGENT - Offers     │          │ posting.yaml           │             │
│  │ 2. HOT - Best matches  │          │ • Company, role, URL   │             │
│  │ 3. PIPELINE - Stale    │          │ • Match score          │             │
│  │ 4. OUTREACH - Referrals│          │ • Events audit log     │             │
│  │ 5. PREP - Interviews   │          │ • Referral candidates  │             │
│  │ 6. TRENDS - Skills     │          └────────────────────────┘             │
│  └────────────────────────┘                                                  │
│              │                                                               │
│              ▼                                                               │
│     ┌─────────────────┐                                                      │
│     │ You wake up,    │                                                      │
│     │ read digest,    │                                                      │
│     │ take action     │                                                      │
│     └─────────────────┘                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

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

## Tech Stack

- **Claude** - Autonomous agent (via claude-code CLI)
- **Beads** - Persistent task state across context windows
- **Gmail API** - OAuth2 for autonomous email access
- **Python** - LinkedIn/Gmail tooling
- **YAML** - Schema-driven data format

## Configuration (The Interface)

Before running, you need to customize these files for your job search:

### 1. `CLAUDE.md` - Your Search Profile

Edit this file to define:
```yaml
# Target roles (agent searches for these)
target_roles:
  - Platform Engineer
  - Site Reliability Engineer
  - DevOps Engineer

# Salary requirements (filters out lower)
salary:
  minimum: 150000
  target: 180000

# Location preferences
location:
  remote: true
  hybrid_cities:
    - Seattle
    - San Francisco

# Two-tier strategy
tiers:
  practice:     # Apply now for interview practice
    - General tech companies
    - Startups
  reserved:     # Save for later, don't burn bridges
    - Your dream companies
    - Target industry (healthcare, fintech, etc.)
```

### 2. `sources.yaml` - Companies to Track

Add companies to the API tracking lists:
```yaml
greenhouse_companies:
  - stripe
  - cloudflare
  - your-target-company  # Add your targets

lever_companies:
  - netflix
  - another-company
```

### 3. Your Resume (Optional)

Place your resume as `resume.pdf` or `resume.txt` for:
- Keyword matching against job descriptions
- Skills gap analysis in the digest

---

## Setup

### Prerequisites

- **Go 1.19+** - For beads installation
- **Python 3.8+** - For Gmail/LinkedIn scripts
- **Claude Code CLI** - `npm install -g @anthropic-ai/claude-code`

### Step 1: Clone and Install Dependencies

```bash
git clone https://github.com/yourusername/job-search-agent
cd job-search-agent

# Python dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install google-auth google-auth-oauthlib google-api-python-client

# Beads (persistent agent memory)
go install github.com/steveyegge/beads/cmd/bd@latest
bd init
```

### Step 2: Gmail OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable the **Gmail API**
4. Create OAuth 2.0 credentials:
   - Application type: **Desktop app**
   - Download as `credentials.json` to repo root
5. Run auth script (opens browser):
   ```bash
   python scripts/gmail-auth.py
   ```
6. Sign in and authorize - creates `gmail-tokens.json`

**Multiple accounts?** Run auth script multiple times, tokens are stored per-email.

### Step 3: LinkedIn Data Export

1. LinkedIn → Settings → Data Privacy → Get a copy of your data
2. Select: Connections, Messages, Profile
3. Wait for email (can take 24 hours)
4. Extract to `linkedin_archive/` folder

Re-export weekly to keep referral data fresh.

### Step 4: Configure Your Profile

Edit `CLAUDE.md` with your:
- Target roles and keywords
- Salary requirements
- Location preferences
- Practice vs reserved companies

### Step 5: Test Run

```bash
# Activate environment
source .venv/bin/activate
export PATH="$PATH:$(go env GOPATH)/bin"

# Test Gmail access
python scripts/gmail-fetch.py accounts
python scripts/gmail-fetch.py list --query "newer_than:7d"

# Test LinkedIn data
python scripts/linkedin-tools.py connections
python scripts/linkedin-tools.py recruiters

# Manual agent run (watch the output)
./scripts/daily-job-search.sh
```

### Step 6: Schedule Cron Jobs

```bash
# Edit crontab
crontab -e

# Add these lines (use absolute paths!)
0 4 * * * /home/you/job-search-agent/scripts/health-check.sh
0 5 * * * /home/you/job-search-agent/scripts/daily-job-search.sh
```

**Important cron notes:**
- Use **absolute paths** everywhere
- The shell scripts handle venv activation and PATH setup
- Logs go to `logs/` directory
- Test manually first before relying on cron

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

## Customization

### Adding New Job Sources

Edit `sources.yaml` to add companies:
```yaml
greenhouse_companies:
  - new-company-name  # Must match their Greenhouse board URL
```

Test with:
```bash
curl https://boards-api.greenhouse.io/v1/boards/new-company-name/jobs
```

### Adjusting Match Scoring

The digest ranks opportunities by score. Tweak weights in `scripts/daily-agent.md`:
- Match rate (keyword overlap with resume)
- Referral bonus (+20 if you have a connection)
- Salary bonus (+10 if above target)
- Recency (newer postings score higher)

### Adding Keywords

Add to `CLAUDE.md` under target skills:
```yaml
must_have:
  - Kubernetes
  - Terraform
  - Python

nice_to_have:
  - Go
  - AWS
```

---

## Troubleshooting

### Gmail: "Access blocked" error
Your OAuth app is in testing mode. Add your email as a test user:
1. Google Cloud Console → APIs & Services → OAuth consent screen
2. Scroll to "Test users" → Add users
3. Add your Gmail address

### Gmail: Token expired
Tokens last indefinitely if you're a test user. If expired:
```bash
rm gmail-tokens*.json
python scripts/gmail-auth.py  # Re-authorize
```

### Cron job not running
```bash
# Check if cron service is running
systemctl status cron

# Check cron logs
grep CRON /var/log/syslog

# Verify absolute paths in crontab
crontab -l
```

### Beads: "command not found"
Add Go bin to your PATH:
```bash
export PATH="$PATH:$(go env GOPATH)/bin"
# Add to ~/.bashrc for persistence
```

### Agent errors
Check logs:
```bash
ls -la logs/
tail -100 logs/daily-job-search-$(date +%Y-%m-%d).log
```

---

## License

MIT

---

Built with Claude Code and too much coffee.
