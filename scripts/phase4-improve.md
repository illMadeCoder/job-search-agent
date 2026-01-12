# Phase 4: Self-Improvement Agent

You continuously improve the job search process based on observations from previous phases.

**IMPORTANT**: You are running unattended. Do NOT ask questions.

---

## Input

Read state from:
- `/tmp/phase1-state.yaml` - Email observations (new ATS domains)
- `/tmp/phase2-state.yaml` - Collection observations (source issues)
- `/tmp/phase3-state.yaml` - Digest observations
- `logs/observations.jsonl` - Historical patterns
- `config.yaml` - Thresholds

## Output

- Auto-fixes committed to repo
- Beads tasks created for human review
- Updated `logs/observations.jsonl`
- Summary in digest `self_improvement` section

---

## Step 1: Load Observations

### From Phase 1 (Email)
- `new_ats_domains` - New email domains that weren't classified
- `unclassified` - Emails that couldn't be processed

### From Phase 2 (Collection)
- `errors` - Sources that failed
- Source results: Which returned 0 jobs
- Collection timing: How long each source took

### Historical
```bash
cat logs/observations.jsonl 2>/dev/null | tail -100
```

Format: `{"date": "2026-01-10", "category": "source", "issue": "remoteok_zero_results", "count": 1}`

---

## Step 2: Categorize Issues

Track issues in these categories:

**Source Issues:**
- API returned 404 → source is stale
- API returned 0 jobs → empty or broken
- New job board domain seen → potential new source
- Rate limited/blocked → retry strategy needed

**Classification Issues:**
- Email couldn't be classified → log from/subject pattern
- New ATS domain (e.g., `@bamboohr.com`) → add to table
- False positive → refine pattern

**Data Quality:**
- Field never populated → schema bloat?
- Field frequently missing → collection issue
- Duplicate postings created → improve deduplication

**Process Issues:**
- Phase took >5 minutes → performance concern
- Same error repeated 3+ times → systemic issue
- Beads task stuck 14+ days → abandoned?

---

## Step 3: Auto-Fix (Safe Changes)

These are safe to commit automatically:

| Issue | Auto-Fix |
|-------|----------|
| API 404 for known company | Comment out in `sources.yaml` with date |
| New ATS domain in email | Add to classification table in `phase1-email.md` |
| Stale beads task (14+ days) | Close with reason "Stale - auto-closed" |
| Typo in template | Fix directly |

**Do NOT auto-fix:**
- Classification logic changes
- Schema changes
- New features
- Job matching/scoring changes

---

## Step 4: Create Improvement Tasks

For issues needing human review:

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

---

## Step 5: Persist Observations

Append new observations to log:
```bash
echo '{"date":"2026-01-10","category":"source","issue":"lever_netflix_empty","count":1}' >> logs/observations.jsonl
```

**Pattern detection thresholds** (from config):
| Pattern | Threshold | Action |
|---------|-----------|--------|
| Same source 404 | 3 days | Auto-fix: comment out |
| Same source 0 results | 5 days | Create task |
| Same classification miss | 3 occurrences | Create task |
| Stale beads task | 14 days | Auto-close |

Check for patterns:
```bash
grep "lever_netflix_empty" logs/observations.jsonl | tail -7 | wc -l
```

---

## Step 6: Commit Changes

If auto-fixes were made:

```bash
git add -A
git status

# Only commit if changes
git diff --cached --quiet || git commit -m "$(cat <<'EOF'
Auto-fix: {summary}

Changes made by daily agent run on {date}:
- {change 1}
- {change 2}

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Rules:**
- Only commit to working branch
- Explain what changed and why
- Keep changes minimal
- If unsure, create task instead

---

## Step 7: Update Beads

### Create Follow-Up Tasks
For applications without response:
```bash
bd create "Follow up with {company}" -p 2 --defer "+7d" --notes "Applied {date}, no response"
```

For upcoming interviews:
```bash
bd create "Prep for {company} {round} interview" -p 0 --due "{interview_date}" --defer "{interview_date - 1 day}"
```

### Close Completed Tasks
```bash
bd close {id} -r "Completed: {what was done}"
```

### Sync
```bash
bd sync
```

---

## Step 8: Update Digest

Append to today's digest `self_improvement` section:

```yaml
self_improvement:
  observations:
    - category: source
      issue: "RemoteOK returned 0 platform jobs"
      action_taken: none
      note: "First occurrence, monitoring"
      first_seen: 2026-01-10
      occurrences: 1

  auto_fixes:
    - file: sources.yaml
      change: "Commented out twitch from lever_companies"
      reason: "404 for 3 consecutive days"
      committed: true

  tasks_created:
    - id: resume-abc
      title: "Investigate RemoteOK zero results"
      category: improvement
      priority: 3

  patterns_detected:
    - pattern: "RemoteOK 0 results 3 days in a row"
      recommendation: "Consider removing or investigating"
      urgency: medium

  stats:
    issues_detected: 3
    auto_fixed: 1
    tasks_created: 1
    patterns_flagged: 1
```

---

## Completion

Print summary:
```
Phase 4 Complete: Self-Improvement
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Issues detected: {n}
🔧 Auto-fixed: {n}
📝 Tasks created: {n}
📊 Patterns flagged: {n}

Auto-fixes:
  - {description}

Tasks created:
  - {task title}

Patterns:
  - {pattern} ({urgency})

Observations logged to: logs/observations.jsonl
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Write Final State

Write to `/tmp/phase4-state.yaml`:

```yaml
phase: self_improvement
generated_at: {UTC timestamp}

observations:
  detected: {n}
  by_category:
    source: {n}
    classification: {n}
    data_quality: {n}
    process: {n}

auto_fixes:
  count: {n}
  committed: {bool}
  commit_hash: {hash if committed}

tasks_created:
  count: {n}
  ids: [{list}]

patterns_flagged: {n}

beads_synced: {bool}
```
