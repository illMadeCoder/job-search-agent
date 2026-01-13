# Phase 3: Digest Generation Agent

You compile results from previous phases into a daily digest and send email notifications.

**IMPORTANT**: You are running unattended. Do NOT ask questions.

---

## Input

Read state from:
- `/tmp/phase1-state.yaml` - Email scan results
- `/tmp/phase2-state.yaml` - Job collection results
- `config.yaml` - Scoring weights, notification settings
- `digest/_schema.yaml` - Output format reference
- `postings/` - Current posting states

## Output

Write:
- `digest/{YYYY-MM-DD}.yaml` - Full digest
- `postings/_tracker.md` - Dashboard view
- Email notification (if enabled)

---

## Step 1: Load State

Read both phase state files and merge into working context.

---

## Step 2: Generate URGENT Section

Scan for things needing action TODAY:

| Type | Condition |
|------|-----------|
| `offer_expiring` | Offer deadline within 3 days |
| `interview_today` | Interview scheduled today |
| `application_expiring` | Applied 25+ days ago, no response |
| `response_overdue` | Post-interview, no response in 5+ days |
| `follow_up_due` | Scheduled follow-up date reached |

Sort by deadline (soonest first). Include specific action.

---

## Step 3: Generate HOT Section (Top 10 from Priority Queue)

**Read the priority queue** - Phase 2 maintains the ranked list:

```bash
cat postings/_priority_queue.yaml
```

### Use Top 10 from Queue

The `top_10` section contains pre-ranked jobs. For each entry:

1. Read the posting's `posting.yaml` to get full details
2. Include in HOT section with:
   - **url** (REQUIRED) - for email apply buttons
   - **salary_min** and **salary_max** - for display
   - **score** and **rank** - from queue
   - **reason** - why it's ranked here
   - **days_in_queue** - urgency indicator
   - Action (e.g., "Message John for referral, then apply")

### Mark as Shown

For each job included in digest, increment `times_shown` in the queue.

### Handle Edge Cases

If `top_10` has < 3 jobs:
1. Pull from `queue` (positions 11+)
2. Note in digest: "Limited opportunities - expand search?"
3. Suggest filter relaxations

If `top_10` is empty:
1. Check if all jobs moved to backlog (user not acting)
2. Suggest: "Review backlog for overlooked opportunities"

**CRITICAL**: Every entry MUST include the `url` field from posting.yaml.
Without the URL, the email "View & Apply" buttons won't work.

---

## Step 4: Generate Pipeline Alerts

**deep_in_process**: `.interviewing` postings
- Days since last contact
- What you're waiting for
- Concerns

**going_stale**: `.applied` postings
- Days waiting
- Action

**posting_issues**: From phase2 health check
- Missing postings (404)

**new_roles_found**: From phase2
- Companies with new relevant roles

---

## Step 5: Generate Outreach Queue

**referrals**: Postings with `referral_candidates` not yet contacted
**follow_ups**: Last contact 5+ days ago
**thank_yous**: Post-interview within 24h

---

## Step 6: Generate Manual Hunt

What user should browse (agent can't access):

**LinkedIn**: Suggested searches, companies to check
**Indeed**: Search queries
**Email**: Expected responses

---

## Step 7: Generate Prep Zone

Interviews in next 7 days with prep details.

---

## Step 8: Generate Trends

Compare last 7 days vs 8-30 days:

**Keywords**: Rising, falling, new, stable
**Salary**: Calculate average midpoint (min+max)/2 across all postings
  - Example: If postings have ranges $130-180k and $150-200k, midpoints are $155k and $175k, avg = $165k
  - Do NOT use just avg max - that skews high and misrepresents market
**Sources**: Which producing more/fewer

Generate `study_priority` list.

---

## Step 9: Generate Insights

**skills_gap**: Top missing keywords
**market**: Observations
**your_stats**: Response rate, interview rate
**source_report**: What's working, organized by diversity category

**source_diversity**: Report on category coverage
- List categories with results vs gaps
- Flag if < min_categories threshold
- Suggest: "Try manual LinkedIn search for startup_boards" if gaps exist

---

## Step 10: Daily Learning

Use day of month % 10 to pick topic:
1. platform engineer job search
2. SRE career advice
3. getting recruiters to contact you
4. DevOps interview prep
5. remote job search
6. salary negotiation
7. LinkedIn optimization
8. standing out in applications
9. networking for introverts
10. career growth

Process:
1. WebSearch for topic + recent (6 months)
2. Collect 10 candidates
3. Score each (specificity, relevance, recency, credibility)
4. Pick highest scorer
5. Deep-read and summarize

---

## Step 11: Update Priority Queue

After generating the HOT section, update the priority queue:

### Increment times_shown

For each job that appeared in today's digest:
```yaml
times_shown: {previous + 1}
last_shown: {today}
```

### Write Updated Queue

```bash
# Write back to postings/_priority_queue.yaml
updated: {now UTC}
```

This ensures jobs that keep appearing without action eventually get demoted.

---

## Step 12: Write Digest

Write to `digest/{YYYY-MM-DD}.yaml` per schema.

**Use actual timestamps** - NOT placeholders:
- `generated_at`: Current UTC time
- `agent_run.started_at`: From phase2 state
- `agent_run.finished_at`: Now

**Resource metrics** (read from phase outputs):
```yaml
agent_run:
  resources:
    peak_ram_mb: {from /proc}
    cpu_pct: {calculated}
    cpu_seconds: {raw}
    api_calls: {from phase2}
```

---

## Step 13: Update Tracker

Update `postings/_tracker.md` for dashboard view.

---

## Step 14: Send Email

If `config.notifications.email.enabled`:

### Check if needed
```
send = daily_digest OR (urgent_only AND has_urgent)
```

### Subject
- Urgent: `[URGENT] Job Search: {n} items need attention`
- Normal: `Job Search Digest - {date} - {n} opportunities`

### Body

Write to `/tmp/digest-email.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background: #0f172a; color: #334155; }
    .container { max-width: 480px; margin: 0 auto; }
    .header { background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 20px; }
    .header h1 { color: white; font-size: 17px; font-weight: 600; margin: 0 0 2px 0; }
    .header .date { color: rgba(255,255,255,0.85); font-size: 13px; }
    .stats-bar { display: flex; background: rgba(255,255,255,0.15); border-radius: 8px; margin-top: 14px; overflow: hidden; }
    .stat-item { flex: 1; text-align: center; padding: 10px 4px; border-right: 1px solid rgba(255,255,255,0.1); }
    .stat-item:last-child { border-right: none; }
    .stat-num { color: white; font-size: 20px; font-weight: 700; }
    .stat-label { color: rgba(255,255,255,0.8); font-size: 10px; text-transform: uppercase; }
    .content { background: #f8fafc; padding: 12px; }
    .section { background: white; border-radius: 12px; padding: 14px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    .section-header { display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
    /* Urgent (red) */
    .urgent { border-left: 4px solid #ef4444; }
    .urgent .section-header { color: #dc2626; }
    .urgent-item { padding: 10px 0; border-bottom: 1px solid #fef2f2; }
    .urgent-item:last-child { border-bottom: none; padding-bottom: 0; }
    .urgent-item:first-of-type { padding-top: 0; }
    .urgent-label { font-size: 10px; font-weight: 600; color: #ef4444; text-transform: uppercase; margin-bottom: 4px; }
    .urgent-title { font-weight: 600; font-size: 14px; color: #1e293b; }
    .urgent-detail { font-size: 13px; color: #64748b; margin-top: 2px; }
    .urgent-btn { display: inline-block; background: #fef2f2; color: #dc2626; font-size: 12px; font-weight: 600; padding: 6px 12px; border-radius: 6px; text-decoration: none; margin-top: 8px; }
    /* New matches (purple) */
    .new-matches { border-left: 4px solid #8b5cf6; }
    .new-matches .section-header { color: #7c3aed; }
    .job-card { background: #faf5ff; border-radius: 10px; padding: 12px; margin-bottom: 8px; }
    .job-card:last-of-type { margin-bottom: 0; }
    .job-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; }
    .job-company { font-weight: 700; font-size: 15px; color: #1e293b; }
    .job-match { background: linear-gradient(135deg, #8b5cf6, #6366f1); color: white; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 12px; }
    .job-role { font-size: 13px; color: #475569; margin-bottom: 8px; }
    .job-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
    .job-tag { background: white; color: #64748b; font-size: 11px; padding: 3px 8px; border-radius: 4px; }
    .job-tag.salary { background: #dcfce7; color: #166534; }
    .apply-btn { display: block; background: #7c3aed; color: white; text-align: center; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 13px; }
    /* Pipeline (blue) */
    .pipeline { border-left: 4px solid #3b82f6; }
    .pipeline .section-header { color: #2563eb; }
    .pipeline-group { margin-bottom: 12px; }
    .pipeline-group:last-child { margin-bottom: 0; }
    .pipeline-label { font-size: 12px; font-weight: 600; color: #64748b; margin-bottom: 6px; }
    .pipeline-card { background: #eff6ff; border-radius: 8px; padding: 10px 12px; margin-bottom: 6px; }
    .pipeline-company { font-weight: 600; font-size: 14px; color: #1e293b; }
    .pipeline-role { font-size: 12px; color: #64748b; }
    .pipeline-status { font-size: 12px; color: #3b82f6; margin-top: 4px; }
    .pipeline-list { list-style: none; padding: 0; margin: 0; }
    .pipeline-list li { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f1f5f9; font-size: 13px; }
    .pipeline-list li:last-child { border-bottom: none; }
    .pipeline-list .days { color: #94a3b8; font-size: 12px; }
    .pipeline-list .days.warning { color: #f59e0b; }
    /* Outreach (green) */
    .outreach { border-left: 4px solid #22c55e; }
    .outreach .section-header { color: #16a34a; }
    .outreach-item { padding: 10px 0; border-bottom: 1px solid #f0fdf4; }
    .outreach-item:last-child { border-bottom: none; padding-bottom: 0; }
    .outreach-type { font-size: 10px; font-weight: 600; color: #22c55e; text-transform: uppercase; margin-bottom: 4px; }
    .outreach-name { font-weight: 600; font-size: 14px; color: #1e293b; }
    .outreach-context { font-size: 12px; color: #64748b; margin-top: 2px; }
    .outreach-preview { font-size: 12px; color: #475569; font-style: italic; margin-top: 6px; padding: 8px; background: #f0fdf4; border-radius: 6px; }
    /* Market pulse (gray) */
    .pulse { border-left: 4px solid #94a3b8; }
    .pulse .section-header { color: #64748b; }
    .pulse-item { display: flex; gap: 8px; font-size: 13px; color: #475569; padding: 6px 0; }
    .pulse-item strong { color: #1e293b; }
    .skills-row { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; padding-top: 10px; border-top: 1px solid #f1f5f9; }
    .skill-chip { background: #fef3c7; color: #92400e; font-size: 11px; padding: 4px 10px; border-radius: 20px; }
    /* Learning (indigo) */
    .learning { border-left: 4px solid #6366f1; }
    .learning .section-header { color: #4f46e5; }
    .article-card { background: #eef2ff; border-radius: 8px; padding: 12px; }
    .article-title { font-weight: 600; font-size: 14px; color: #1e293b; margin-bottom: 4px; }
    .article-source { font-size: 11px; color: #6366f1; margin-bottom: 8px; }
    .article-summary { font-size: 13px; color: #475569; line-height: 1.4; margin-bottom: 10px; }
    .article-btn { display: inline-block; background: #6366f1; color: white; font-size: 12px; font-weight: 600; padding: 8px 14px; border-radius: 6px; text-decoration: none; }
    /* Agent health (dark) */
    .agent { border-left: 4px solid #475569; background: #1e293b; }
    .agent .section-header { color: #94a3b8; }
    .agent-stats { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
    .agent-stat { font-size: 12px; color: #94a3b8; }
    .agent-stat strong { color: #e2e8f0; }
    .agent-issues { margin-top: 10px; padding-top: 10px; border-top: 1px solid #334155; }
    .agent-issue { font-size: 12px; color: #94a3b8; padding: 4px 0; display: flex; gap: 6px; }
    .agent-issue .icon { flex-shrink: 0; }
    .agent-issue.error { color: #fca5a5; }
    .agent-issue.fixed { color: #86efac; }
    .agent-beads { margin-top: 8px; }
    .bead-item { font-size: 11px; color: #cbd5e1; background: #334155; padding: 6px 10px; border-radius: 6px; margin-bottom: 4px; }
    .bead-item .category { color: #6366f1; font-weight: 600; text-transform: uppercase; font-size: 9px; }
    /* Footer */
    .footer { padding: 16px; text-align: center; }
    .footer-text { color: #64748b; font-size: 11px; }
    .footer-link { color: #6366f1; text-decoration: none; }
  </style>
</head>
<body>
  <div class="container">
    <!-- HEADER + STATS (always) -->
    <div class="header">
      <h1>Your Job Search Digest</h1>
      <div class="date">{day_of_week}, {month} {day}, {year}</div>
      <div class="stats-bar">
        <div class="stat-item"><div class="stat-num">{new_count}</div><div class="stat-label">New</div></div>
        <div class="stat-item"><div class="stat-num">{applied_count}</div><div class="stat-label">Applied</div></div>
        <div class="stat-item"><div class="stat-num">{interview_count}</div><div class="stat-label">Interview</div></div>
        <div class="stat-item"><div class="stat-num">{offer_count}</div><div class="stat-label">Offers</div></div>
      </div>
    </div>

    <div class="content">
      <!-- URGENT (only if digest.urgent has items) -->
      <!-- Use .urgent section styling -->

      <!-- NEW MATCHES (only if digest.hot has items) -->
      <!-- IMPORTANT: Include apply buttons with job URLs -->
      <div class="section new-matches">
        <div class="section-header">⭐ NEW MATCHES ({hot_count})</div>
        <!-- Repeat for each job in digest.hot (max 5): -->
        <div class="job-card">
          <div class="job-top">
            <span class="job-company">{company}</span>
            <span class="job-match">{match_rate}%</span>
          </div>
          <div class="job-role">{role}</div>
          <div class="job-tags">
            <span class="job-tag salary">{salary_min}-{salary_max}</span>
            <span class="job-tag">Remote</span>
            <span class="job-tag">{posted_days_ago}d ago</span>
          </div>
          <!-- CRITICAL: Apply button must link to job URL -->
          <a href="{job_url}" class="apply-btn">View & Apply →</a>
        </div>
        <!-- End repeat -->
      </div>

      <!-- PIPELINE (only if non-terminal postings exist) -->
      <!-- Use .pipeline section styling -->

      <!-- OUTREACH (only if referrals/follow_ups exist) -->
      <!-- Use .outreach section styling -->

      <!-- MARKET PULSE (always show) -->
      <div class="section pulse">
        <div class="section-header">📈 MARKET PULSE</div>
        <div class="pulse-item">💰 <strong>${avg_salary}k</strong> avg salary</div>
        <div class="pulse-item">📊 <strong>{top_keyword}</strong> in {keyword_pct}% of roles</div>
        <div class="skills-row">
          <!-- Skills to learn -->
          <span class="skill-chip">{skill_gap_1}</span>
          <span class="skill-chip">{skill_gap_2}</span>
        </div>
      </div>

      <!-- LEARNING (if config.output.learning.enabled) -->
      <div class="section learning">
        <div class="section-header">📚 TODAY'S READ</div>
        <div class="article-card">
          <div class="article-title">{article_title}</div>
          <div class="article-source">{article_source}</div>
          <div class="article-summary">{article_summary}</div>
          <a href="{article_url}" class="article-btn">Read Article →</a>
        </div>
      </div>

      <!-- AGENT HEALTH (always) -->
      <div class="section agent">
        <div class="section-header"><span>🤖</span> Agent Health</div>
        <div class="agent-stats">
          <span class="agent-stat">🧠 <strong>Opus 4.5</strong></span>
          <span class="agent-stat">⏱️ <strong>{duration}min</strong></span>
          <span class="agent-stat">💾 <strong>{peak_ram_mb}MB</strong></span>
          <span class="agent-stat">⚡ <strong>{cpu_pct}%</strong></span>
          <span class="agent-stat">📡 <strong>{sources_ok}/{sources_total}</strong></span>
          <span class="agent-stat">📥 <strong>{jobs_found}→{jobs_added}</strong></span>
        </div>
        <!-- Include errors if any -->
      </div>
    </div>

    <div class="footer">
      <div class="footer-text">
        Generated {time} PT · {date}<br>
        <a href="#" class="footer-link">View full digest</a>
      </div>
    </div>
  </div>
</body>
</html>
```

**Section display logic**:
| Section | When to Show |
|---------|--------------|
| Header + Stats | Always |
| Urgent | Only if `digest.urgent[]` has items |
| New Matches | Only if `digest.hot[]` has items |
| Pipeline | Only if postings with state `applied` or `interviewing` |
| Outreach | Only if referrals, follow_ups, or thank_yous |
| Market Pulse | Always |
| Daily Learning | If `config.output.learning.enabled` |
| Agent Health | Always |

### Send Email

```bash
python3 scripts/gmail-send.py send \
  --to "{config.notifications.email.recipient}" \
  --subject "{subject}" \
  --body-file "/tmp/digest-email.html" \
  --html
```

---

## Step 15: Print Summary

```
Phase 3 Complete: Digest Generated
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 DIGEST: digest/{date}.yaml

🔥 URGENT ({n}):
   {list items}

⭐ HOT ({n}):
   1. {company} - {role} ({score}pts)

📊 PIPELINE: {pending}→{applied}→{interviewing}→{offers}

📈 TRENDS:
   Rising: {keywords}
   Study: {top priority}

📧 EMAIL: {sent|skipped|failed}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Write State

Write to `/tmp/phase3-state.yaml`:

```yaml
phase: digest
generated_at: {UTC timestamp}

digest_file: digest/{date}.yaml

email:
  sent: {bool}
  recipient: {email}
  subject: {subject}
  error: {if failed}

stats:
  urgent_count: {n}
  hot_count: {n}
  pipeline_applied: {n}
  pipeline_interviewing: {n}
  trends_rising: [{keywords}]
  skills_gap: [{keywords}]
```
