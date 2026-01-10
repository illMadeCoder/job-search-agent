# Health Check Agent

Daily health check for job postings. Runs at 4am before the main job search agent.

**Read first**: `config.yaml` for target roles and timing settings.

## Purpose

1. Verify job posting URLs are still active
2. Find new relevant roles at companies you've applied to
3. Flag applications needing review

## Instructions

### Phase 1: Check Existing Postings

For each posting folder in `postings/` that is NOT in a terminal state (offer, rejected, expired, withdrawn):

1. **Read posting.yaml** to get the original job URL
2. **Fetch the URL** using WebFetch
3. **Evaluate status**:
   - If 200 and contains job description → `status: active`
   - If 404 or no job content → `status: missing`
   - If redirects to careers page (job gone) → `status: closed`

4. **Update posting.yaml**:
   ```yaml
   status: active  # or missing, closed
   ```

5. **Add health_check event**:
   ```yaml
   events:
     - timestamp: "2026-01-10T04:00:00Z"
       type: health_check
       data:
         posting_status: active  # or missing
         new_roles_found: []     # filled in Phase 2
   ```

6. **If posting is missing/closed**:
   - Rename folder to add `.review` suffix: `company.applied/` → `company.applied.review/`
   - This flags it for user attention

### Phase 2: Scan for New Roles

For each company with an active application (state = applied or interviewing):

1. **Identify careers page**:
   - Try: `https://careers.{company}.com`
   - Try: `https://{company}.com/careers`
   - Search: `{company} careers jobs`

2. **Look for new relevant roles** matching `config.search.target_roles`:
   - Read target roles from config.yaml
   - Search for each role type at the company

3. **If new roles found**:
   - Add to health_check event's `new_roles_found`
   - Add `.review` suffix to folder if not already present
   - Log for digest

### Phase 3: Write Summary

Write summary to `logs/health-check-{YYYY-MM-DD}.md`:

```markdown
# Health Check - {DATE}

## Summary
- Postings checked: N
- Active: N
- Missing: N (list)
- New roles found: N

## Missing Postings (need review)
- company-name.applied.review/ - URL returned 404

## New Roles at Applied Companies
- company-name: "Senior SRE" at https://...

## Errors
- (any failures)
```

### Phase 4: Prepare for Job Search

The 5am job search agent will:
- See `.review` folders in its summary
- Include missing postings in digest's `pipeline_alerts.posting_issues`
- Include new roles in digest's `pipeline_alerts.new_roles_found`

## Folder Naming Reference

```
postings/
├── acme-corp.pending_review/      # Awaiting your review
├── acme-corp.applied/             # Applied, watching
├── acme-corp.applied.review/      # Applied, needs attention!
├── acme-corp.interviewing/        # In interview process
├── acme-corp.interviewing.review/ # Interviewing, issue found!
├── acme-corp.offer/               # Terminal: got offer
├── acme-corp.rejected/            # Terminal: rejected
├── acme-corp.expired/             # Terminal: no response
└── acme-corp.withdrawn/           # Terminal: you withdrew
```

States that need checking: `pending_review`, `applied`, `interviewing`
Terminal states (skip): `offer`, `rejected`, `expired`, `withdrawn`

## Error Handling

- If URL fetch fails (timeout, network error): log error, don't change status
- If careers page not found: skip new role scan, log it
- If parsing fails: log raw response for debugging
- Continue to next posting on any error

## Timing

Runs at 4am, before 5am job search:
```
0 4 * * * /path/to/your/repo/scripts/health-check.sh
0 5 * * * /path/to/your/repo/scripts/daily-job-search.sh
```
