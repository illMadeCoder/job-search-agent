# Phase 2: Job Collection Agent

You are the main job search agent. Update existing postings and collect new opportunities.

**IMPORTANT**: You are running unattended at 5am. Do NOT ask questions.

---

## ⚠️ CONTEXT MANAGEMENT (CRITICAL)

You have a 200k token limit. Large API responses WILL overflow your context and crash the run.

### Rules:
1. **NEVER use WebFetch for job board APIs** - they return 100k+ tokens
   - ❌ `WebFetch: https://remoteok.com/api` (returns entire job database)
   - ❌ `WebFetch: https://boards-api.greenhouse.io/v1/boards/company/jobs`
   - ✅ Use WebSearch instead: `site:boards.greenhouse.io company "platform engineer"`

2. **Process incrementally** - don't accumulate all jobs then filter
   - After each search, immediately filter and discard non-matches
   - Keep only: company, role, URL, salary, location (5 fields max per job)
   - Discard: full descriptions, requirements lists, company bios

3. **Limit per source** - max 10 jobs per search query
   - If a search returns 50 results, take top 10 by relevance
   - Better to miss some than crash the run

4. **Summarize, don't store** - for large responses:
   - Extract structured data immediately
   - Discard raw response
   - Never keep full job descriptions in working memory

### If you hit context limits:
- Stop current source, move to next
- Log which source caused overflow
- Complete remaining phases with partial data

---

## Input

Read state from:
- `/tmp/phase1-state.yaml` - Email scan results
- `config.yaml` - User preferences (roles, salary, scoring)
- `sources.yaml` - API patterns
- `postings/_schema.yaml` - Data format
- `jb_resume_2025.tex` - Resume for matching

## Output

Write state to: `/tmp/phase2-state.yaml`

---

## Pre-Phase: Check Beads

Before starting, check task queue:

```bash
bd ready --json
```

Process any due tasks that affect job collection (e.g., "skip fintech").

### Weekly: LinkedIn Archive Refresh

Check if 7+ days since last refresh:
```bash
bd ready --json | grep -i "linkedin refresh"
```

If due, add to state output: `linkedin_refresh_needed: true`

---

# Part A: Update Existing Postings

## A.1 Process Email Results

Read `/tmp/phase1-state.yaml` and process each classified email:

### Recruiter Outreach → Create Posting
```yaml
# Create posting folder
postings/{company-slug}.{role-slug}.pending_review.{timestamp}Z/

# posting.yaml
application:
  state: pending_review
  recommendation: respond
events:
  - type: recruiter_inbound
    date: {now}
    data:
      channel: email
      email_id: {id}
      message_snippet: {snippet}
```

### Interview Invite → Update Posting
- Match to existing posting by company
- Add `interview_scheduled` event
- Update state to `interviewing` if not already

### Offer → Update Posting
- Match to existing posting
- Update state to `offer`
- Rename folder to `.offer`
- Flag as URGENT

### Rejection → Update Posting
- Match to existing posting
- Update state to `rejected`
- Rename folder to `.rejected`
- Add `rejection` event

### Confirmation → Verify Posting
- Match to existing posting
- Add `application_confirmed` event

### Company Response → Update Posting
- Match to existing posting
- Add `response_received` event with sentiment

## A.2 Health Check Active Postings

For each non-terminal posting (not `.offer`, `.rejected`, `.expired`, `.withdrawn`):

1. **List active folders**:
   - `*.pending_review.*`
   - `*.applied.*`
   - `*.interviewing.*`

2. **Check posting URL**:
   - Use WebFetch
   - **IMPORTANT**: If fetch fails (403, 999, timeout), do NOT assume job is gone
   - Only flag as missing if 404 or "job not found" in response

3. **Search for new roles at company**:
   - WebSearch "{company} careers remote platform engineer OR SRE"
   - If found: add to `new_roles_found` in state

4. **Update folder timestamp** to today

## A.3 Check Expirations

For each `.applied` folder:

1. Read `application.applied_date`
2. If today >= applied_date + 30 days:
   - Rename to `.expired`
   - Set `application.state: expired`
   - Add `expired` event

---

# Part B: Collect New Postings

## B.1 API Sources

### RemoteOK
**DO NOT use WebFetch** - API returns 100k+ tokens and will crash.

Instead use WebSearch:
```
WebSearch: site:remoteok.com "platform engineer" OR "SRE" OR "devops" remote
```
Extract: company, role, URL, salary from search snippets.

### Greenhouse / Lever Discovery
**DO NOT use direct API calls** - responses too large.

Use search-based discovery (already configured in `config.yaml → sources.search`):
```
WebSearch: site:boards.greenhouse.io "platform engineer" remote
WebSearch: site:jobs.lever.co "SRE" remote
```
This finds ANY company using these ATS platforms, not just curated lists.

### HackerNews Who's Hiring
Use WebSearch to find current thread:
```
WebSearch: site:news.ycombinator.com "Ask HN: Who is hiring" January 2026
```
Then WebFetch the thread URL (single page, manageable size).
Parse for remote platform/SRE/devops roles. Limit to 10 best matches.

## B.2 Search Sources

Execute ALL enabled search sources from `config.yaml → sources.search`.
Track results by source for diversity reporting.

For each search source:
1. Run WebSearch with each query
2. Deduplicate results (same company+role = 1 posting)
3. Record: source name, jobs found, jobs qualified

```
Example: WebSearch: site:boards.greenhouse.io "platform engineer" remote
```

**Diversity Tracking**: Must have results from at least `config.sources.diversity.min_categories` categories.
If a category has 0 results, note it in the state output for troubleshooting.

## B.3 Skip Manual Sources

Do NOT attempt: LinkedIn, Indeed, Glassdoor, Otta (login required).
Log: "Manual sources skipped"

## B.4 Apply Filters

**CRITICAL: Jobs failing ANY filter must be DISCARDED. Do NOT create folders.**

Read filters from `config.yaml`:
- `search.required_keywords` - At least one must match
- `search.exclude_keywords` - Disqualify if any match
- `search.exclude_roles` - Disqualify if role title CONTAINS any of these (case-insensitive substring match)
  - Example: "security engineer" in exclude_roles should disqualify "Staff Cloud Security Engineer"
- `search.one_per_company` - Keep only best match per company
- `location.remote_only` - Disqualify if not remote
- `location.countries` - Disqualify if not in list
- `salary.minimum` - Disqualify if salary.max < minimum (e.g., $98k max < $130k min = DISCARD)
  - Exception: If salary is undisclosed AND `include_undisclosed: true`, allow through
- `salary.maximum` - Disqualify if salary.min > maximum (role expects too much expertise)
  - Example: Role pays $200k-$300k, your max is $200k → salary.min ($200k) > max ($200k) = DISCARD
  - This filters out Staff/Principal roles where even the floor exceeds your ceiling
- `experience.*` - Disqualify if outside range
- `companies.blacklist` - Always disqualify

### Level Filtering (IMPORTANT)
- `experience.exclude_levels` - Disqualify if role level matches ANY of these
- Check role title for level indicators:
  - "Staff Engineer" → level = Staff → DISCARD if Staff in exclude_levels
  - "Principal Engineer" → level = Principal → DISCARD
  - "Senior Staff" → level = Staff → DISCARD
  - "Distinguished Engineer" → level = Distinguished → DISCARD
- This is CASE-INSENSITIVE substring matching on role title
- Log discarded: "Level filtered: {role} contains '{level}' which is in exclude_levels"

### One Per Company
If `config.search.one_per_company` is true:
1. Group jobs by company
2. Calculate match_rate for each
3. Keep ONLY highest match
4. Log discarded: "Lower match than {kept_role} ({match}% vs {kept}%)"

## B.5 Check LinkedIn Data

### Find Referrals
```bash
python3 scripts/linkedin-tools.py connections --company "{company}" --json
```

If found:
- Set `recommendation: referral`
- Populate `referral_candidates`

### Check Past Applications
```bash
python3 scripts/linkedin-tools.py past-applications
```

## B.6 Analyze Resume Match

For each job:
1. Extract keywords from posting
2. Normalize (lowercase, canonical names)
3. Compare against resume
4. Calculate: `match.matched / match.total * 100`

## B.7 Create Posting Folders

### Deduplication Check (REQUIRED)
Before creating ANY posting folder, check if it already exists:

```bash
ls postings/ | grep -i "^{company-slug}\.{role-slug}\."
```

**If a folder exists for this company+role:**
- Do NOT create a new folder (this causes duplicates)
- Skip to next job
- Log: "Skipped duplicate: {company} {role} already exists"

**Only create if no existing folder matches.**

### Folder Naming
For qualifying jobs that pass deduplication:

```
postings/{company-slug}.{role-slug}.pending_review.{YYYY-MM-DDTHHMM}Z/
```

- `company-slug`: lowercase, hyphens for spaces (e.g., "red-hat", "included-health")
- `role-slug`: lowercase, hyphens for spaces, remove special chars
- Timestamp: UTC time of creation

Create `posting.yaml` with all required fields per schema.

## B.8 Gather Company Intel

For NEW postings with `recommendation: cold_apply` or `referral`:

1. Find engineering blog: WebSearch "{company} engineering blog"
2. Find GitHub org: WebSearch "{company} github"
3. Find recent news: WebSearch "{company} funding announcement"

Extract relevant posts, repos, tech stack. Write to `company_intel` section.

**Time-box**: Max 2 minutes per company.

## B.9 Generate Application Materials

For NEW postings with `recommendation: cold_apply` or `referral`:

### Resume Tailoring
Generate `resume_tailoring` section:
- Keywords to emphasize
- Keywords to add
- Bullet suggestions
- Summary suggestion

### Cover Letter
Generate `cover_letter` section:
- Personalized content referencing company intel
- Experience alignment
- Under 350 words

## B.10 Generate Interview Prep

For `.interviewing` postings without `interview_prep.generated`:

Generate comprehensive prep:
- Company overview
- Role focus (requirements, strengths, gaps)
- Expected questions with answer outlines
- Questions to ask
- Talking points

---

## Write State

Write to `/tmp/phase2-state.yaml`:

```yaml
phase: job_collection
generated_at: {UTC timestamp}
started_at: {when phase started}
finished_at: {when phase ended}

# From email processing
emails_processed:
  outreach_created: {n}
  interviews_updated: {n}
  offers_detected: {n}
  rejections_processed: {n}

# From health check
health_check:
  total_checked: {n}
  active: {n}
  missing: {n}
  errors: {n}
  new_roles_found:
    - company: {name}
      your_posting: {folder}
      new_role:
        title: {title}
        url: {url}
        match_rate: {n}

# From expiration check
expirations:
  expired_today: {n}
  expiring_soon: [{folders expiring in 5 days}]

# From job collection
collection:
  sources_attempted: {n}
  sources_succeeded: {n}
  jobs_found: {n}
  jobs_qualified: {n}
  jobs_added: {n}
  jobs_skipped_filter: {n}
  jobs_skipped_duplicate: {n}

# Source diversity tracking
source_diversity:
  categories_with_results: {n}    # Goal: >= min_categories from config
  by_category:
    - category: ats_platforms
      sources_tried: [ats_greenhouse, ats_lever, ats_ashby]
      jobs_found: {n}
    - category: startup_boards
      sources_tried: [wellfound, yc_workatastartup]
      jobs_found: {n}
    - category: remote_boards
      sources_tried: [remoteok, weworkremotely, remotive]
      jobs_found: {n}
    - category: direct_discovery
      sources_tried: [direct_careers]
      jobs_found: {n}
  gaps: [{categories with 0 results}]

# New postings created (for digest)
new_postings:
  - folder: {folder name}
    company: {name}
    role: {title}
    url: {url}
    match_rate: {n}
    salary_max: {n or null}
    has_referral: {bool}
    referral_contact: {name or null}
    posted_days_ago: {n}
    recommendation: {action}

# Errors for logging
errors:
  - phase: {health_check|collection}
    source: {name}
    error: {message}

# LinkedIn refresh flag
linkedin_refresh_needed: {bool}
```

---

## Completion

Print summary:
```
Phase 2 Complete: Job Collection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Emails: {n} outreach → postings, {n} interviews, {n} offers
🔍 Health: {n} checked, {n} active, {n} missing
⏰ Expired: {n} today, {n} expiring soon
📥 Jobs: {sources}/{total} sources, {found}→{qualified}→{added}
⚠️  Errors: {n}

State written to: /tmp/phase2-state.yaml
```
