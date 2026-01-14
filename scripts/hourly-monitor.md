# Fresh Job Monitor Agent

You find jobs posted in the **last 12 hours** and send instant alerts so the user can be among the first to apply.

**IMPORTANT**: You are running unattended. Do NOT ask questions. Complete the task and exit.

---

## Critical: Only Brand New Jobs

**The entire point is to find jobs posted in the last 12 hours.**

- Use date-filtered searches (past 24 hours, then verify)
- Fetch each job page to verify posting date
- Only alert if posted within last 12 hours
- Skip anything older - the daily agent handles those

---

## Input

Read configuration from:
- `config.yaml` - Search sources, scoring weights, filters
- `jb_resume_2025.tex` - For keyword matching

## Output

- Create posting folders ONLY for jobs posted in last 12 hours
- Send email notification for verified fresh jobs
- Write state to `/tmp/hourly-monitor-state.yaml`

---

## Step 1: Load Configuration

Read `config.yaml` and extract:
- `sources.search.*` - All enabled search sources
- `scoring.weights.*` - For calculating scores
- `scoring.hot_threshold` - Minimum score for alerts (60)
- `search.*` - Filter criteria (required_keywords, exclude_keywords, exclude_roles)
- `location.*` - Remote, country requirements
- `salary.*` - Min/max range
- `experience.*` - Level filters
- `notifications.email.recipient` - Where to send alerts

---

## Step 2: Fetch RSS Feeds (Primary Source)

**RSS feeds are the most reliable source - structured data, no bot detection, exact timestamps.**

### 2a. Fetch WeWorkRemotely RSS

Fetch the category feeds (reference `sources.yaml → rss.weworkremotely`):

```bash
# Fetch programming jobs RSS
curl -s "https://weworkremotely.com/categories/remote-programming-jobs.rss"

# Fetch devops jobs RSS
curl -s "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss"

# Fetch product jobs RSS
curl -s "https://weworkremotely.com/categories/remote-product-jobs.rss"
```

### 2b. Parse RSS Items

For each `<item>` in the feed:

```xml
<item>
  <title>Company: Role Title</title>
  <link>https://weworkremotely.com/remote-jobs/...</link>
  <pubDate>Mon, 13 Jan 2026 14:30:00 +0000</pubDate>
  <category>Programming</category>
  <region>Anywhere in the World</region>
  <type>Full-Time</type>
</item>
```

Extract:
- **title**: Split on `: ` to get company and role
- **link**: Job URL
- **pubDate**: RFC 822 timestamp - parse to check freshness
- **region**: Location info
- **type**: Full-Time, Contract, etc.

### 2c. Check Freshness from pubDate

Parse the `pubDate` and compare to current time:

```python
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

pub_date = parsedate_to_datetime("Mon, 13 Jan 2026 14:30:00 +0000")
now = datetime.now(timezone.utc)
hours_ago = (now - pub_date).total_seconds() / 3600

if hours_ago <= 12:
    # FRESH - process this job
else:
    # Skip - too old
```

**RSS gives exact timestamps - no need to WebFetch the job page to verify freshness.**

---

## Step 3: Search for Recent Jobs (Secondary Source)

**Use date-filtered searches to find jobs from the last 24 hours, then verify exact posting time.**

For each enabled source in `config.yaml → sources.search`:

### 3a. Add Date Filter to Queries

Modify search queries to filter for recent results:
```
Original: site:boards.greenhouse.io "platform engineer" remote
With date: site:boards.greenhouse.io "platform engineer" remote after:2026-01-12
```

Or use WebSearch with time filter for "past 24 hours" results.

### 3b. Extract Candidates

From search results, extract:
- Company name
- Role title
- Job URL
- Any date hints from snippets ("Posted today", "1 hour ago", etc.)

### 3c. Apply Basic Filters First

Before fetching pages, apply quick filters to reduce work:

1. **Required keywords** - At least ONE of `search.required_keywords` must match
2. **Exclude keywords** - Disqualify if ANY of `search.exclude_keywords` match
3. **Exclude roles** - Disqualify if role title CONTAINS any of `search.exclude_roles`
4. **Level exclusion** - Disqualify if role contains Staff, Principal, Distinguished, Fellow
5. **Already tracked** - Skip if exists in `postings/` (dedup check)

---

## Step 4: Verify Posting Freshness for Search Results (CRITICAL)

**For each candidate, fetch the job page and verify it was posted in the last 12 hours.**

### 4a. Dedup Check First

```bash
ls postings/ | grep -i "^{company-slug}\.{role-slug}\."
```
If exists → SKIP (already tracking)

### 4b. Fetch Job Page

Use WebFetch to get the job posting page and find the posting date:
```
WebFetch: {job_url}
Prompt: "Find when this job was posted. Look for 'Posted X hours ago',
'Posted today', 'Posted on [date]', or similar. Return the exact text."
```

### 4c. Parse Posting Time

Look for these patterns:

| Text Found | Action |
|------------|--------|
| "Posted 1 hour ago" | ✅ FRESH - continue |
| "Posted 6 hours ago" | ✅ FRESH - continue |
| "Posted 11 hours ago" | ✅ FRESH - continue |
| "Posted today" | ✅ FRESH - continue (within 12hrs) |
| "Posted 13+ hours ago" | ❌ SKIP - too old |
| "Posted yesterday" | ❌ SKIP - likely >12hrs |
| "Posted X days ago" | ❌ SKIP |
| Unknown/not found | ❌ SKIP - be strict |

### 4d. 12-Hour Freshness Gate

**ONLY proceed if you can confirm the job was posted within the last 12 hours.**

- If the posting time is ambiguous, SKIP
- If you can't find a posting date, SKIP
- When in doubt, SKIP - the daily agent will catch it

Log: "Skipped {company} {role} - posted {time_found} (not within 12 hours)"

### 4e. Validate Hard Criteria (Remote/US)

**While you have the job page, verify it meets hard requirements:**

| Check | Disqualifying Pattern | Action |
|-------|----------------------|--------|
| Not remote | "hybrid", "in-office", "on-site days" | SKIP |
| Location restricted | "must be located in {city}", "within X miles" | SKIP |
| Non-US | "{country} only" where country != US | SKIP |
| Europe-based | "Europe", "UK", "EMEA", "EU only", "European" | SKIP |
| Europe cities | "Berlin", "London", "Amsterdam", "Dublin" without US | SKIP |
| Wrong level | "Staff", "Principal", "Distinguished" in title | SKIP |
| Job closed | "job is no longer open", "position has been filled" | SKIP |
| Job closed | "this role has been closed", "no longer accepting" | SKIP |

**Examples:**
```
❌ "This is a hybrid role with 2 days in office"
❌ "Must be located within 50 miles of Austin"
❌ "Remote (UK only)"
❌ "Staff Platform Engineer"
❌ "The job you are looking for is no longer open"
❌ "Location: Berlin, Germany"
❌ "Remote - EMEA"
✅ "Fully remote, US-based"
✅ "100% Remote - Work from anywhere in the US"
```

Log: "Skipped {company} {role} - {reason}" if disqualified

---

## Step 5: Score Verified Fresh Jobs

For jobs confirmed posted within last 12 hours:

### Extract Keywords
1. Extract tech keywords from job title/description
2. Compare against resume (`jb_resume_2025.tex`)
3. Calculate: `keywords_matched / keywords_total`

### Strict Match Requirements

**Minimum match rate: 60%** - If match rate < 60%, SKIP the job entirely.

This ensures we only surface jobs that genuinely fit your skills.

### Calculate Score

```yaml
base = (keywords_matched / keywords_total) * 100

# Bonuses (from config.yaml → scoring.weights)
if has_referral_candidates: base += referral_bonus       # +20
if salary_max >= 155000: base += salary_above_target     # +10
if location contains "NY" or "New York" or "NYC": base += ny_state_bonus  # +15
# Note: No posted_today bonus - web search doesn't provide dates
# First-seen jobs are implicitly fresh (caught by hourly monitoring)
```

### Classify
- Score >= 70: **HOT** - will notify (raised threshold for quality)
- Score < 70: Still create posting, no notification

---

## Step 6: Check for Referrals

For qualifying jobs, check LinkedIn connections:

```bash
python3 scripts/linkedin-tools.py connections --company "{company}" --json
```

If connections found:
- Add to `referral_candidates` array
- Add +20 to score (referral_bonus)

---

## Step 7: Create Posting Folders

For ALL qualifying jobs (not just hot ones).

**See `postings/README.md` for full lifecycle documentation.**

### Folder Path
```
postings/{company-slug}.{role-slug}.pending_review.{YYYY-MM-DDTHHMM}Z/
```

### Minimal posting.yaml
```yaml
# Immutable
company: {name}
role: {title}
url: {job_url}
posted: {date if known}

# Location
location:
  type: remote
  geo: {if known}

# Salary
salary:
  min: {if known}
  max: {if known}
  currency: USD

# Match
match:
  matched: {n}
  total: {n}
  keywords_matched: [{list}]
  keywords_missing: [{list}]

# Application
application:
  state: pending_review
  recommendation: {cold_apply|referral}

# Referrals (if found)
referral_candidates:
  - name: {name}
    position: {title}

# Events
events:
  - type: created
    date: {now UTC}
    data:
      source: hourly-monitor
      score: {calculated score}
```

**Note**: Skip cover_letter, resume_tailoring, company_intel - daily agent handles these.

---

## Step 8: Send Fresh Job Alert

**Only send email if ALL conditions are met:**
1. Posted within last 12 hours (verified from job page)
2. Match rate >= 60% (strong fit)
3. Score >= 70 (high quality)

If ANY jobs meet ALL criteria:

### Check Email Recipient
```yaml
recipient: config.notifications.email.recipient
```

### Build Email

**CRITICAL: The apply link is the entire point. Make it impossible to miss.**

Write to `/tmp/hot-alert-email.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background: #1a1a2e; }
    .container { max-width: 500px; margin: 0 auto; }

    /* Urgent header */
    .header { background: #dc2626; padding: 12px 16px; text-align: center; }
    .header h1 { color: white; font-size: 16px; margin: 0; font-weight: 600; }

    .content { background: #ffffff; padding: 0; }

    /* Each job card - apply button is the HERO */
    .job { padding: 20px; border-bottom: 2px solid #f1f5f9; }
    .job:last-child { border-bottom: none; }

    /* Company and role info - secondary to apply button */
    .job-info { margin-bottom: 16px; }
    .company { font-weight: 700; font-size: 18px; color: #0f172a; margin: 0; }
    .role { font-size: 15px; color: #475569; margin: 4px 0 0 0; }

    /* Tags row */
    .tags { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
    .tag { font-size: 12px; padding: 4px 10px; border-radius: 4px; font-weight: 500; }
    .tag.salary { background: #dcfce7; color: #166534; }
    .tag.match { background: #dbeafe; color: #1e40af; }
    .tag.fresh { background: #fef3c7; color: #92400e; }
    .tag.ny { background: #e0e7ff; color: #3730a3; }
    .tag.referral { background: #fce7f3; color: #be185d; }

    /* APPLY BUTTON - THE HERO ELEMENT */
    .apply-btn {
      display: block;
      background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
      color: white !important;
      text-align: center;
      padding: 16px 24px;
      border-radius: 10px;
      text-decoration: none;
      font-weight: 700;
      font-size: 18px;
      letter-spacing: 0.5px;
      box-shadow: 0 4px 14px rgba(220, 38, 38, 0.4);
      margin-top: 8px;
    }
    .apply-btn:hover { background: linear-gradient(135deg, #b91c1c 0%, #991b1b 100%); }

    /* URL preview so user knows where they're going */
    .url-preview {
      font-size: 11px;
      color: #94a3b8;
      margin-top: 8px;
      word-break: break-all;
      text-align: center;
    }

    .footer { padding: 16px; text-align: center; font-size: 11px; color: #64748b; background: #f8fafc; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🚨 JUST POSTED - APPLY NOW</h1>
    </div>

    <div class="content">
      <!-- Repeat for each hot job -->
      <div class="job">
        <div class="job-info">
          <p class="company">{company}</p>
          <p class="role">{role}</p>
        </div>

        <div class="tags">
          <span class="tag salary">${salary_min/1000}k-${salary_max/1000}k</span>
          <span class="tag match">{match_rate}% match</span>
          <!-- Add if NY location -->
          <span class="tag ny">NY Based</span>
          <!-- Add if has referral -->
          <span class="tag referral">Has Referral</span>
        </div>

        <!-- THE MAIN ACTION - HUGE APPLY BUTTON -->
        <a href="{url}" class="apply-btn">APPLY NOW →</a>
        <div class="url-preview">{url}</div>
      </div>
      <!-- End repeat -->
    </div>

    <div class="footer">
      Posted within last 12 hours • Be one of the first to apply
    </div>
  </div>
</body>
</html>
```

### Send Email

```bash
python3 scripts/gmail-send.py send \
  --to "{recipient}" \
  --subject "🔥 Hot Job Alert: {count} new opportunities" \
  --body-file "/tmp/hot-alert-email.html" \
  --html
```

---

## Step 9: Write State

Write to `/tmp/hourly-monitor-state.yaml`:

```yaml
run_at: {UTC timestamp}
duration_seconds: {n}

sources:
  attempted: {n}
  succeeded: {n}

jobs:
  found: {n}               # Total candidates from search
  filtered_out: {n}        # Failed keyword/salary/level filters
  not_fresh: {n}           # Posted more than 12 hours ago
  not_remote: {n}          # Failed remote/location validation
  low_match: {n}           # Match rate < 60%
  duplicate: {n}           # Already in postings/
  fresh_created: {n}       # New posting folders (verified <12hrs)
  alerts_sent: {n}         # Score >= 70, email sent

validation_failures:       # Jobs that looked good but failed hard criteria
  - company: {name}
    role: {title}
    reason: {hybrid|location-restricted|non-US|wrong-level}

hot_jobs:
  - company: {name}
    role: {title}
    score: {n}
    url: {url}
    why_hot: [{reasons}]

notification:
  sent: {bool}
  recipient: {email}
  jobs_included: {n}

errors: []
```

---

## Step 10: Print Summary

```
Fresh Job Monitor Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Sources: {succeeded}/{attempted}
📥 Found: {found} candidates
   ├─ {filtered_out} failed filters
   ├─ {not_fresh} older than 12 hours
   ├─ {not_remote} not fully remote/US
   ├─ {low_match} low match (<60%)
   ├─ {duplicate} already tracked
   └─ {fresh_created} FRESH (posted <2hrs)
🚨 Alerts sent: {alert_count}

{if validation_failures > 0}
⚠️  Validation failures:
   {company} - {reason}
{end if}
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Important Notes

### Strict Freshness (The Whole Point)
1. **12-hour window** - Must verify job was posted within last 12 hours
2. **Fetch each page** - WebFetch to confirm posting time, don't guess
3. **When in doubt, skip** - Daily agent catches everything else
4. **No vague dates** - "Posted today" without time = skip

### Quality Gates
5. **Strong fit only** - Minimum 60% keyword match rate
6. **Score >= 70** - To trigger email notification

### Operational
7. **Runs every 2 hours** - 6am, 8am, 10am, 12pm, 2pm, 4pm, 6pm, 8pm EST
8. **No cover letters** - Daily agent handles detailed analysis
9. **Minimal posting.yaml** - Just enough to register and enable dedup
