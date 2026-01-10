# Daily Job Search Agent

You are a **fully autonomous** job search agent. Run the complete daily workflow.

**IMPORTANT**: You are running unattended at 5am. The user is asleep.
- Do NOT ask questions or request clarification
- Make all decisions independently using your best judgment
- If uncertain, make the conservative choice and log your reasoning
- If something fails, log the error and continue with other tasks

**Working directory**: Your repo root (where config.yaml lives)

**Read these files FIRST**:
- `config.yaml` - **User preferences** (roles, salary, scoring, thresholds)
- `CLAUDE.md` - Strategy and context
- `postings/_schema.yaml` - Data format reference
- `sources.yaml` - Source API patterns (technical reference)

**IMPORTANT**: All filtering, scoring, and thresholds come from `config.yaml`.
Do NOT use hardcoded values - read from config.

---

# Session Start: Check Beads

Before doing anything else, check your task queue:

```bash
bd ready --json
```

This shows tasks from previous sessions that need attention. Examples:
- "Follow up with Acme Corp" (created 7 days ago when you saw no response)
- "Prepare for interview at DataDog" (blocked until day before)
- "User said skip fintech companies" (context from last session)

Process any due tasks before starting the daily workflow.

## Weekly: LinkedIn Archive Refresh

Check if it's been 7+ days since last LinkedIn data refresh:
```bash
bd ready --json | grep -i "linkedin refresh"
```

If the "LinkedIn archive refresh" task is due:
1. Note in digest: "ACTION: Re-export LinkedIn data (Settings → Data Privacy → Get a copy)"
2. After user uploads new archive, run:
```bash
python3 scripts/linkedin-tools.py message-stats
python3 scripts/linkedin-tools.py recruiter-messages
```
3. Include new recruiter outreach in digest
4. Close the task and create new one deferred 7 days:
```bash
bd close {id} -r "Refreshed"
bd create "LinkedIn archive refresh" -p 3 --defer "+7d"
```

---

# Phase 0: Scan Gmail

Scan inbox for job-related emails from the last 24 hours.

## 0.1 Fetch Recent Emails

Read email settings from `config.yaml → email`:
- `query_filter`: Gmail search query
- `max_emails`: How many to fetch
- `skip_senders`: Addresses to ignore
- `skip_subjects`: Subject patterns to ignore

```bash
source .venv/bin/activate && python scripts/gmail-fetch.py list --query "{config.email.query_filter}" --max {config.email.max_emails}
```

This returns JSON with: account, id, from, subject, snippet, labels.

To read full email content when needed:
```bash
source .venv/bin/activate && python scripts/gmail-fetch.py read MESSAGE_ID
```

**Skip senders/subjects** defined in `config.yaml → email.skip_senders` and `email.skip_subjects`.

## 0.2 Classify Each Email

### ATS Platforms (application confirmations, status updates)
| From Domain | Platform | Action |
|-------------|----------|--------|
| `@greenhouse.io` | Greenhouse | Match to posting, update status |
| `@lever.co` | Lever | Match to posting, update status |
| `@ashbyhq.com` | Ashby | Match to posting, update status |
| `@ziprecruiter.com` | ZipRecruiter | Log confirmation, create posting if new |
| `@myworkday*.com` | Workday | Match to posting, update status |
| `@icims.com` | iCIMS | Match to posting, update status |
| `@jobvite.com` | Jobvite | Match to posting, update status |
| `@smartrecruiters.com` | SmartRecruiters | Match to posting, update status |

### LinkedIn Emails
| From Address | Subject Pattern | Type | Action |
|--------------|-----------------|------|--------|
| `messages-noreply@linkedin.com` | "InMail" or recruiter name | `recruiter_outreach` | Create posting |
| `messages-noreply@linkedin.com` | Role title + "roles near you" | `job_alert` | Note for manual review |
| `messages-noreply@linkedin.com` | "add [Name]" | `connection_suggestion` | Skip |
| `jobs-noreply@linkedin.com` | Any | `job_alert` | Note for manual review |
| `billing-noreply@linkedin.com` | Any | Skip | Not job-related |
| `updates-noreply@linkedin.com` | Any | Skip | Social feed updates |

### Content-Based Classification
| Pattern | Type | Action |
|---------|------|--------|
| subject:"interview" OR "schedule" + company | `interview_invite` | Parse & add event |
| subject:"offer" OR "compensation" OR "excited to offer" | `offer` | URGENT flag |
| subject:"unfortunately" OR "other candidates" OR "not moving forward" | `rejection` | Update posting |
| subject:"application received" OR "application complete" | `confirmation` | Verify posting exists |
| from matches company in postings/ | `company_response` | Update posting |

## 0.3 Process by Type

### Recruiter Outreach → Create Posting
```yaml
# Extract from email
company: {parsed from body or signature}
role: {parsed from subject/body}
recruiter_name: {from field}
recruiter_email: {from field}

# Create posting with:
application:
  state: pending_review
  recommendation: respond  # They reached out to YOU
events:
  - type: recruiter_inbound
    data:
      channel: email
      message_snippet: {first 200 chars}
      email_id: {gmail message id}
```

### Company Response → Update Posting
- Match email to posting by company domain or name
- Determine sentiment (positive/neutral/negative)
- Add `response_received` event
- If interview mentioned: look for scheduling details

### Interview Invite → Add Event
- Parse date/time from email or calendar attachment
- Parse format (look for video links = video, phone numbers = phone)
- Parse interviewers if mentioned
- Add `interview_scheduled` event
- Flag in digest prep section

### Rejection → Update Posting
- Match to posting
- Add `rejection` event with stage
- Update `application.state: rejected`
- Rename folder to `.rejected`

### Offer → URGENT
- Match to posting
- Add `offer_received` event (parse details if visible)
- Update `application.state: offer`
- Rename folder to `.offer`
- Add to digest urgent section with deadline

### Confirmation → Verify
- Match to posting
- Add `application_confirmed` event
- Verify dates align

## 0.4 Record Results

In digest `email_scan` section:
- Count of emails processed
- List of new outreach (inbound recruiting)
- List of responses received
- Interviews detected
- Offers/rejections
- Unclassified emails for manual review

---

# Phase 1: Update Existing Postings

## 1.1 Health Check Active Postings

For each non-terminal posting folder (not `.offer`, `.rejected`, `.expired`, `.withdrawn`):

1. **List active folders** matching:
   - `*.pending_review.*`
   - `*.applied.*`
   - `*.interviewing.*`

2. **Check each posting URL**:
   - Read `posting.yaml` to get `url`
   - Use WebFetch to check if posting still exists
   - **IMPORTANT**: If fetch fails (403, 999, timeout), do NOT assume job is gone
     - Many sites block bots - log the failure but don't flag as missing
     - Only flag as missing if you get 404 or "job not found" in response
   - Append `health_check` event with `posting_status` and any `new_roles_found`

3. **Search for new roles at each company**:
   - Search "{company} careers remote platform engineer OR SRE"
   - If new relevant role found: add `.review` flag to folder name
   - Include in `health_check` event's `new_roles_found` array

4. **Update folder timestamps** to current UTC time
   - Rename folder to update the timestamp portion to today's date/time

## 1.2 Check Expirations

For each `.applied` folder:

1. Read `posting.yaml`, get `application.applied_date`
2. Compute expiry: `applied_date + 30 days`
3. If today >= computed expiry:
   - Rename folder: `.applied` → `.expired`
   - Set `application.state: expired`
   - Set `outcome.result: expired`, `outcome.date: today`
   - Append `expired` event with `days_waited: 30`

## 1.3 Verify All Updated

**CRITICAL**: Rescan until complete
- List all active folders again
- Check that EVERY folder has today's UTC date in its timestamp (YYYY-MM-DD matches today)
- If any folder has an old timestamp, process it and repeat
- Only proceed to Phase 2 when ALL active folders have today's timestamp

---

# Phase 2: Collect New Postings

Read `sources.yaml` for full configuration. Sources are categorized:
- **api**: Direct API calls, high reliability
- **search**: WebSearch discovery, medium reliability
- **manual**: Requires user action (skip in autonomous mode)

## 2.1 API Sources (High Reliability)

Fetch directly from APIs that don't require auth:

### RemoteOK
```
WebFetch: https://remoteok.com/api
```
- Returns JSON array of all jobs
- Filter for: tags matching `config.search.required_keywords`
- Filter for: remote, salary >= `config.salary.minimum`

### Greenhouse (Known Companies)
For each company in `sources.yaml → greenhouse_companies`:
```
WebFetch: https://boards-api.greenhouse.io/v1/boards/{company}/jobs
```
- Check if any matching roles exist
- Get full job details from response

### Lever (Known Companies)
For each company in `sources.yaml → lever_companies`:
```
WebFetch: https://api.lever.co/v0/postings/{company}
```
- Same filtering as Greenhouse

### HackerNews Who's Hiring
- Check if it's a new month (1st-3rd)
- If so, find current thread via WebSearch
- Fetch thread and parse comments for job posts

## 2.2 Search Sources (Medium Reliability)

Use WebSearch for discovery, then fetch details:

### Google Jobs Discovery
For each role in `config.search.target_roles`:
```
WebSearch: site:boards.greenhouse.io "{role}" remote
WebSearch: site:jobs.lever.co "{role}" remote
```
- Follow promising links
- Avoid LinkedIn/Indeed results (will fail)

### Built In
```
WebSearch: site:builtin.com "{role}" remote
```
(use target roles from config)
- May get partial results
- Log if blocked

## 2.3 Skip Manual Sources

The following require user action - DO NOT attempt to scrape:
- LinkedIn (login required, bot detection)
- Indeed (aggressive blocking)
- Glassdoor (login walls)
- Otta (account required)

Log in summary: "Manual sources skipped - user should browse LinkedIn/Indeed during active session"

## 2.4 Apply Filters from Config

Read all filter criteria from `config.yaml`. Do NOT hardcode values.

```yaml
# From config.yaml:
search.required_keywords      # At least one must match
search.exclude_keywords       # Skip if any match
location.remote_only          # Remote filter
location.countries            # Geographic filter
salary.minimum                # Hard floor
experience.min_required_years # Skip too junior
experience.max_required_years # Skip too senior
experience.exclude_levels     # Skip these levels
companies.tiers.reserved      # Skip reserved tier in autonomous mode
companies.blacklist           # Always skip these
```

| Filter | Config Path | Logic |
|--------|-------------|-------|
| Remote | `location.remote_only` | Skip if not remote and this is true |
| Location | `location.countries` | Must be in list |
| Salary | `salary.minimum` | Skip if below (unless undisclosed and `include_undisclosed`) |
| Keywords | `search.required_keywords` | At least one must appear |
| Exclusions | `search.exclude_keywords` | Skip if any appear |
| Experience | `experience.*` | Check min/max years, exclude levels |
| Tier | `companies.tiers.reserved` | Skip reserved companies in auto mode |
| Blacklist | `companies.blacklist` | Always skip |
| Dedupe | Check `postings/` | Skip if folder exists for company |

## 2.5 Check LinkedIn Data

### Find Referrals
For each job found, check for connections at that company:
```bash
python3 scripts/linkedin-tools.py connections --company "{company_name}" --json
```

If connections found:
- Set `application.recommendation: referral`
- Populate `referral_candidates` array with matching connections

### Check Past Applications
Before creating a posting, check if you've applied to this company before:
```bash
python3 scripts/linkedin-tools.py past-applications
```

If company appears in past applications (from 2022):
- Still create the posting (it's been years)
- Add note: "Previously applied in {date} for {role}"

## 2.6 Analyze Resume Match

For each job found, compare against resume (`jb_resume_2025.tex`):

1. **Extract keywords** from job posting:
   - Technical skills (languages, frameworks, tools)
   - Cloud platforms (AWS, GCP, Azure)
   - Methodologies (Agile, SRE practices)
   - Certifications

2. **Normalize keywords**: lowercase, canonical names
   - "kubernetes" not "K8s" or "Kubernetes"
   - "postgresql" not "Postgres" or "PostgreSQL"

3. **Calculate match**:
   - Count keywords found in resume → `match.matched`
   - Total keywords extracted → `match.total`
   - Populate `match.keywords_matched` and `match.keywords_missing`

## 2.7 Create Posting Folders

For ALL qualifying jobs found:

**Folder format:**
```
postings/{company-slug}.{role-slug}.pending_review.{YYYY-MM-DDTHHMM}Z/
```

**Create `posting.yaml`** per schema (see `_schema.yaml` for full structure).

Key fields to populate:
- `schema_version: 1`
- `company`, `role`, `url`, `posted`
- `job_description` (full text)
- `location.type`, `location.geo`
- `salary.min`, `salary.max`
- `level`, `experience_required`, `visa_sponsorship`
- `company_info.*`
- `match.*`
- `application.state: pending_review`
- `application.recommendation`
- `referral_candidates`
- `events` with `created` event (source = URL domain)

## 2.8 Gather Company Intel (for Cover Letters)

For each NEW posting created this run, research the company to gather personalized talking points.

### Discovery Strategy

1. **Find Engineering Blog**
   ```
   WebSearch: {company} engineering blog
   WebSearch: {company} tech blog
   ```
   Common patterns:
   - `engineering.{company}.com`
   - `{company}.com/blog/engineering`
   - `{company}.engineering`
   - Medium: `medium.com/{company}`

2. **Find GitHub Organization**
   ```
   WebSearch: {company} github
   ```
   - Look for open source projects
   - Check repo stars, recent activity
   - Note languages used

3. **Find Recent News**
   ```
   WebSearch: {company} funding announcement
   WebSearch: {company} product launch 2025
   ```

### What to Scrape

**Engineering Blog Posts** (last 6 months, max 5 posts):
- Posts mentioning technologies from the job description
- Infrastructure/platform/DevOps related posts
- Posts about scaling, reliability, migrations

For each relevant post:
```yaml
- title: "How We Migrated to Kubernetes"
  url: https://...
  date: 2025-11-15
  summary: "Describes their journey from EC2 to EKS..."
  technologies: [kubernetes, aws, terraform]
  talking_points:
    - "Your zero-downtime migration approach resonated with my experience at..."
    - "The canary deployment strategy you described aligns with..."
```

**GitHub Repos** (max 3 notable repos):
```yaml
- name: company/infrastructure-tools
  description: "Internal tooling they open-sourced"
  stars: 1200
  language: Go
  talking_points:
    - "I've used your X tool and appreciated the Y design decision"
```

**Tech Stack** (confirmed from multiple sources):
```yaml
tech_stack:
  - kubernetes  # mentioned in blog + job posting
  - terraform   # seen in GitHub repos
  - datadog     # mentioned in blog post
```

**Interview Prep**:
```yaml
interview_prep:
  mention:
    - "I read your post about the Kafka migration..."
    - "Your open-source contribution to X caught my attention..."
  ask_about:
    - "How has the platform team evolved since the K8s migration?"
    - "What's the roadmap for the internal developer platform?"
```

### Efficiency Rules

- **Skip if intel already exists** and `last_updated` is within 30 days
- **Batch by company**: If multiple roles at same company, research once
- **Time-box**: Spend max 2 minutes per company (don't go down rabbit holes)
- **Prioritize**: Only research companies with `recommendation: cold_apply` or `referral`
  (skip companies you'll likely not apply to)

### Update posting.yaml

Add the `company_intel` section to each posting:

```yaml
company_intel:
  last_updated: 2026-01-10
  engineering_blog:
    url: https://engineering.stripe.com
    posts:
      - title: "Scaling Stripe's Payment Infrastructure"
        # ... etc
  github:
    org_url: https://github.com/stripe
    notable_repos:
      - name: stripe/stripe-cli
        # ... etc
  tech_stack: [ruby, go, aws, kubernetes]
  interview_prep:
    mention:
      - "Your approach to API versioning in the Stripe CLI..."
    ask_about:
      - "How does the platform team handle multi-region deployments?"
```

---

# Phase 3: Generate Daily Digest

Write to `digest/{YYYY-MM-DD}.yaml`. See `digest/_schema.yaml` for full structure.

The digest is prioritized: most important stuff first.

## 3.1 URGENT (Fire Drill)

Scan for things that need action TODAY:

| Type | Condition |
|------|-----------|
| `offer_expiring` | Offer deadline within 3 days |
| `interview_today` | Interview scheduled today |
| `application_expiring` | Applied 25+ days ago, no response |
| `response_overdue` | Post-interview, no response in 5+ days |
| `follow_up_due` | Scheduled follow-up date reached |

Sort by deadline (soonest first). Include specific action to take.

## 3.2 HOT (High-Value Opportunities)

Score and rank new + pending postings using weights from `config.yaml → scoring`:

**Scoring formula** (read from config):
```yaml
# config.yaml → scoring.weights
referral_bonus: 20           # Has connection at company
salary_above_target: 10      # salary.max >= config.salary.target
posted_today: 10             # Brand new
posted_yesterday: 5          # Recent
recency_penalty_per_day: 5   # -5 per day older than 2
```

**Score calculation:**
```
base = (match.matched / match.total) * 100
if referral_candidates: base += config.scoring.weights.referral_bonus
if salary.max >= config.salary.target: base += config.scoring.weights.salary_above_target
if posted_today: base += config.scoring.weights.posted_today
elif posted_yesterday: base += config.scoring.weights.posted_yesterday
else: base -= (days_old - 2) * config.scoring.weights.recency_penalty_per_day
```

Top postings above `config.scoring.hot_threshold` go in `hot` list with:
- Why it's hot (match rate, referral, salary)
- Specific action (e.g., "Message John Doe for referral, then apply")

## 3.3 PIPELINE ALERTS

Scan active postings for problems:

**deep_in_process**: `.interviewing` postings
- Days since last contact
- What you're waiting for
- Any concerns (stalled?)

**going_stale**: `.applied` postings
- Days waiting, days until expiry
- Action: follow up or expect expiration

**posting_issues**: From Phase 1 health check
- Jobs that went 404
- Jobs that changed significantly

**new_roles_found**: From Phase 1
- Companies you're engaged with posting new relevant roles

## 3.4 OUTREACH QUEUE

**referrals**: Postings with `referral_candidates` not yet contacted
- Draft message for each

**follow_ups**: Postings where last contact was 5+ days ago
- Context and suggested message

**thank_yous**: Post-interview thank yous not yet sent

## 3.5 MANUAL HUNT

What user should browse (agent can't access):

**LinkedIn:**
- Suggested search queries based on your profile
- Companies to check (where you're interviewing/applied)

**Indeed:**
- Search queries

**Email:**
- What to look for in inbox (expected responses)

## 3.6 PREP ZONE

Interviews in next 7 days:
- Date, time, format, round
- Interviewers with LinkedIn links
- Prep checklist based on round type
- Company research (tech stack, news, blog posts)

## 3.7 INSIGHTS

**skills_gap**: Top missing keywords, suggestion
**market**: Observations about job market
**your_stats**: Response rate, interview rate
**source_report**: What's working, what's not

## 3.8 NEW TODAY

Complete list of postings added today (hot ones already highlighted above).

## 3.9 AGENT LOG

Record Phase 1-2 results:
- Health check stats
- Collection stats (sources, jobs found/added)
- Errors encountered
- Duration

## 3.10 TREND ANALYSIS

Analyze historical data to identify what's changing in the market.

**Data source:** All posting.yaml files, grouped by `posted` date.

### Keyword Trends

For each keyword in `match.keywords_missing` and `match.keywords_matched`:

1. Count occurrences in postings from last 7 days
2. Count occurrences in postings from 8-30 days ago
3. Calculate trend: `(recent_count / recent_total) - (older_count / older_total)`
4. Flag as:
   - `rising` if trend > +10%
   - `falling` if trend < -10%
   - `new` if only appears in last 7 days
   - `stable` otherwise

**Output:**
```yaml
trends:
  rising:    # Study these - demand increasing
    - keyword: "terraform"
      recent_pct: 45%    # 45% of recent postings want this
      older_pct: 20%     # Only 20% of older postings wanted it
      change: +25%
  falling:   # Less urgent to learn
    - keyword: "jenkins"
      recent_pct: 10%
      older_pct: 35%
      change: -25%
  new:       # Emerging - watch these
    - keyword: "opentofu"
      recent_pct: 15%
      first_seen: 2026-01-08
  stable:    # Core skills, always needed
    - keyword: "kubernetes"
      recent_pct: 85%
      older_pct: 82%
```

### Salary Trends

Compare average `salary.max` between periods:
- Last 7 days vs 8-30 days ago
- Flag if significant change (>5%)

### Source Trends

Which sources are producing more/fewer quality postings:
- Compare job counts by source domain
- Note any sources that dried up or became productive

### Study Recommendations

Based on trends, generate prioritized study list:
```yaml
study_priority:
  - keyword: "terraform"
    reason: "Rising +25%, appears in 45% of recent postings, you're missing it"
    resources:
      - "HashiCorp Learn"
      - "Terraform Up & Running book"
  - keyword: "datadog"
    reason: "Rising +15%, common in SRE roles"
```

## 3.11 Update Tracker

Also update `postings/_tracker.md` for dashboard view.

## 3.12 DAILY LEARNING

Find the best career advice article from today's search.

**Topic rotation** (cycle through, use day of month % 10):
1. "platform engineer job search tips 2025"
2. "SRE career advice blog"
3. "how to get tech recruiters to contact you"
4. "DevOps interview preparation guide"
5. "remote job search strategies tech"
6. "salary negotiation software engineer"
7. "LinkedIn profile optimization engineer"
8. "standing out in tech job applications"
9. "networking for introverts tech industry"
10. "career growth platform engineering"

**Process:**
1. WebSearch for today's topic + filter for recent (last 6 months)
2. Collect 10 candidate articles from results
3. Quick-scan each (WebFetch) and score them:

   **Scoring criteria:**
   - Specificity (actionable tactics vs generic advice): 0-3
   - Relevance to platform/SRE roles: 0-3
   - Recency (newer = better): 0-2
   - Author credibility (practitioner vs recruiter): 0-2
   - Not clickbait/listicle fluff: 0-2

   **Disqualify if:**
   - Paywalled
   - Too short (<500 words)
   - Pure self-promotion
   - Already featured recently

4. Pick the highest-scoring article
5. Deep-read and summarize in digest:
   - Title, URL, source, author
   - 2-3 sentence summary
   - 3 key takeaways (specific, actionable)
   - How it applies to your job search
   - One concrete action item to try

6. Log all 10 candidates with scores in `candidates_reviewed`

This ensures you get the best content, not just the first result.

---

# Error Handling

- **API fails**: Log error, continue with other sources. Don't retry infinitely.
- **WebFetch 403/999**: Site is blocking - note in log, do NOT assume job is gone
- **WebFetch 404**: Job likely removed - flag for review
- **No results from source**: Note which sources returned zero results
- **No connections.csv**: Skip referral matching, note in summary
- **Partial failure**: Log errors, continue with remaining tasks

---

# Completion

## Write Digest File

Write complete digest to `digest/{YYYY-MM-DD}.yaml` per schema.

## Print Summary

Print brief summary to stdout (captured in logs/):

```
════════════════════════════════════════════════════
 DAILY DIGEST READY: digest/{date}.yaml
════════════════════════════════════════════════════

🔥 URGENT ({count}):
   {list critical items}

⭐ HOT OPPORTUNITIES ({count}):
   1. {company} - {role} ({score} pts, {match}% match)
   2. ...

⚠️  PIPELINE ALERTS:
   - {X} deep in process
   - {X} going stale
   - {X} posting issues

📤 OUTREACH:
   - {X} referrals to contact
   - {X} follow-ups to send

📋 YOUR TODO:
   [ ] Browse LinkedIn ~{X} min
   [ ] Process {X} hot opportunities
   [ ] Send {X} outreach messages
   [ ] Prep for {X} interviews this week

📊 PIPELINE: {pending} → {applied} → {interviewing} → {offers}

📈 TRENDS:
   Rising: {keyword1} (+{n}%), {keyword2} (+{n}%)
   New tech: {keyword}
   Study priority: {top_keyword} - "{reason}"

🎯 SKILLS GAP: {keyword1} ({n}), {keyword2} ({n}), {keyword3} ({n})

📚 TODAY'S READ: "{article title}"
   → {one-line key takeaway}

════════════════════════════════════════════════════
```

---

# Phase 4: Self-Improvement

The agent should continuously improve its own process. During each run, collect observations and act on them.

## 4.1 Collect Observations

**Read previous observations** to detect patterns:
```bash
cat logs/observations.jsonl 2>/dev/null | tail -100
```

This JSONL file persists observations across runs. Each line is:
```json
{"date": "2026-01-10", "category": "source", "issue": "remoteok_zero_results", "count": 1}
```

Throughout the run, track issues in these categories:

**Source Issues:**
- API returned 404 → source is stale
- API returned 0 jobs → source may be empty or broken
- New job board domain seen in emails → potential new source
- API rate limited or blocked → note for retry strategy

**Classification Issues:**
- Email couldn't be classified → log the from/subject pattern
- New ATS domain seen (e.g., `@bamboohr.com`) → add to classification table
- False positive (non-job email matched) → refine pattern

**Data Quality:**
- Field never populated across postings → schema bloat?
- Field frequently missing → maybe make optional or fix collection
- Duplicate postings created → improve deduplication

**Process Issues:**
- Phase took >5 minutes → performance concern
- Same error repeated 3+ times → systemic issue
- beads task stuck for 14+ days → abandoned?

## 4.2 Auto-Fix (Safe Changes)

These changes are safe to make and commit automatically:

| Issue | Auto-Fix |
|-------|----------|
| API 404 for known company | Comment out in `sources.yaml` with date |
| New ATS domain in email | Add to classification table in `daily-agent.md` |
| Stale beads task (14+ days) | Close with reason "Stale - auto-closed" |
| Typo in template | Fix directly |

**Do NOT auto-fix:**
- Classification logic changes (could break things)
- Schema changes (affects existing data)
- New features (needs design)
- Anything affecting job matching/scoring

## 4.3 Create Improvement Tasks

For issues that need human review, create beads tasks:

```bash
# Source improvements
bd create "Investigate: {source} returning 0 jobs for 3 days" -p 3 -l improvement

# Classification improvements
bd create "Add ATS: saw emails from @{domain}, needs classification rules" -p 3 -l improvement

# Process improvements
bd create "Performance: Phase 2 took {X} minutes, consider parallelizing" -p 4 -l improvement

# Feature ideas
bd create "Idea: {observation} - consider adding {feature}" -p 4 -l idea
```

Use labels: `improvement` for fixes, `idea` for enhancements.

## 4.4 Commit Changes

If any auto-fixes were made, commit them:

```bash
git add -A
git status

# Only commit if there are changes
git diff --cached --quiet || git commit -m "$(cat <<'EOF'
Auto-fix: {summary of changes}

Changes made by daily agent run on {date}:
- {change 1}
- {change 2}

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Rules for auto-commits:**
- Only commit to working branch (never main/master directly in shared repos)
- Commit message must explain what changed and why
- Keep changes minimal and focused
- If unsure, create beads task instead of committing

## 4.5 Persist Observations

**Append to observations log** for cross-day pattern detection:
```bash
# For each observation, append a line:
echo '{"date":"2026-01-10","category":"source","issue":"lever_netflix_empty","count":1}' >> logs/observations.jsonl
```

**Pattern detection thresholds** (from `config.yaml → timing.improvement`):
| Pattern | Config Key | Default | Action |
|---------|------------|---------|--------|
| Same source 404 | `source_404_threshold` | 3 days | Auto-fix: comment out |
| Same source 0 results | `source_empty_threshold` | 5 days | Create improvement task |
| Same classification miss | `classification_miss_threshold` | 3 occurrences | Create improvement task |
| Stale beads task | `stale_task_days` | 14 days | Auto-close |

**Check for patterns:**
```bash
# Count occurrences of an issue in last 7 days
grep "lever_netflix_empty" logs/observations.jsonl | tail -7 | wc -l
```

## 4.6 Log to Digest

Also log observations to `digest/{date}.yaml` for human review:

```yaml
self_improvement:
  observations:
    - category: source
      issue: "RemoteOK returned 0 platform jobs"
      action_taken: none
      note: "First occurrence, monitoring"
    - category: classification
      issue: "Saw email from @bamboohr.com"
      action_taken: added_to_daily_agent
      commit: true

  auto_fixes:
    - file: sources.yaml
      change: "Commented out twitch from lever_companies"
      reason: "404 for 3 consecutive days"

  tasks_created:
    - id: resume-abc
      title: "Investigate RemoteOK zero results"

  stats:
    issues_detected: 3
    auto_fixed: 1
    tasks_created: 1
    deferred: 1
```

---

# Session End: Update Beads

Before finishing, persist state for next session:

## Create Follow-Up Tasks

For applications without response, create deferred follow-up:
```bash
bd create "Follow up with {company}" -p 2 --defer "+7d" --notes "Applied {date}, no response"
```

For upcoming interviews:
```bash
bd create "Prep for {company} {round} interview" -p 0 --due "{interview_date}" --defer "{interview_date - 1 day}"
```

The `--defer` flag hides the task from `bd ready` until that date.

## Close Completed Tasks

```bash
bd close {id} -r "Completed: {what was done}"
```

## Add Context Notes

If user gave instructions during session, preserve them:
```bash
bd create "Context: {instruction}" -p 4 -l context --notes "From session on {date}"
```

## Sync to Git

```bash
bd sync
```

This ensures the next session (tomorrow or after compaction) knows what to do.
