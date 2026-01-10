# Gmail API Integration

## Overview

Agent scans Gmail daily to:
- Detect recruiter outreach → create new postings
- Find company responses → update posting state
- Parse interview invites → add scheduled events
- Flag urgent items (offers, deadlines)

---

## Setup

### 1. Google Cloud Project

```bash
# Go to: https://console.cloud.google.com/

1. Create new project: "job-search-agent"
2. Enable Gmail API:
   APIs & Services → Enable APIs → Gmail API → Enable
3. Configure OAuth consent screen:
   - User type: External (or Internal if Workspace)
   - App name: "Job Search Agent"
   - Scopes: gmail.readonly (start read-only, add modify later if needed)
4. Create OAuth credentials:
   - Type: Desktop application
   - Download JSON → save as `credentials.json` in repo root
```

### 2. Initial Authentication

First run requires browser auth to get refresh token:

```bash
# One-time setup (run manually, not in cron)
claude -p "Authenticate with Gmail using credentials.json, save tokens to gmail-tokens.json"
```

This creates `gmail-tokens.json` with refresh token for autonomous access.

### 3. Files

```
/home/illm/resume/
├── credentials.json      # OAuth client config (from Google Cloud)
├── gmail-tokens.json     # Access/refresh tokens (auto-generated)
└── .gitignore           # Must include both above!
```

**Add to .gitignore:**
```
credentials.json
gmail-tokens.json
```

---

## Agent Email Scanning

### Phase 0: Scan Gmail (New Phase)

Add before Phase 1 in daily-agent.md:

```
# Phase 0: Scan Gmail

Scan all emails from last 24 hours (or since last scan).

## 0.1 Fetch Recent Emails

Using Gmail API:
- Query: `newer_than:1d`
- Get: subject, from, to, date, body (text + html)
- Max: 100 emails per run

## 0.2 Classify Each Email

For each email, determine type:

| Pattern | Classification |
|---------|----------------|
| from:*@linkedin.com subject:"job" | linkedin_job_alert |
| from:*@linkedin.com subject:"InMail" | recruiter_outreach |
| from:*@indeed.com | indeed_alert |
| from:*@greenhouse.io | ats_communication |
| from:*@lever.co | ats_communication |
| from:*@ashbyhq.com | ats_communication |
| from:*@workday.com | ats_communication |
| subject contains "interview" | interview_related |
| subject contains "offer" | offer_related |
| subject contains "unfortunately" OR "moved forward" | rejection |
| subject contains "application received" | application_confirm |
| from matches company in postings/ | company_response |

## 0.3 Process by Type

### Recruiter Outreach (create posting)
- Extract: company, role, recruiter name/email
- Check if company already in postings/
- If new: create posting with state=pending_review, source=recruiter_inbound
- Add event: type=recruiter_inbound

### Company Response (update posting)
- Match to existing posting by company name or email domain
- Add event: type=response_received
- Update contacts if new person
- If positive sentiment: flag for review

### Interview Invite
- Parse for: date, time, format (video link = video, phone number = phone)
- Match to posting
- Add event: type=interview_scheduled
- Add to digest urgent/prep sections

### Application Confirmation
- Match to posting (by company or job title)
- Verify applied_date matches
- Log confirmation

### Rejection
- Match to posting
- Add event: type=rejection
- Update posting state
- Move folder to .rejected

### Offer
- Match to posting
- Add event: type=offer_received (parse salary if visible)
- URGENT flag in digest
- Move folder to .offer

## 0.4 Log Processed Emails

Track in digest:
- Emails scanned: N
- Classified: N by type
- Actions taken: N postings created, N updated
- Unclassified: N (review manually)
```

---

## Email Parsing Patterns

### Recruiter InMail (LinkedIn)
```
From: *@linkedin.com
Subject: contains "InMail" or "message from"

Extract:
- Recruiter name: from "Name via LinkedIn"
- Company: regex in body for "at {Company}" or "{Company} is hiring"
- Role: regex for job titles
```

### Greenhouse/Lever ATS
```
From: *@greenhouse.io OR *@lever.co
Subject: varies

Common patterns:
- "Application received" → confirmation
- "Interview" → scheduling
- "Next steps" → positive response
- "Update on your application" → could be either
- "Unfortunately" → rejection
```

### Calendar Invites
```
Content-Type: text/calendar

Parse .ics attachment:
- SUMMARY: Interview title
- DTSTART: Date/time
- LOCATION: Video link or address
- ATTENDEE: Interviewers
```

---

## Digest Integration

Add to digest schema:

```yaml
# === EMAIL SCAN ===
email_scan:
  last_scan: datetime
  emails_processed: number

  new_outreach:           # Recruiters who contacted you
    - from: string
      company: string
      role: string
      posting_created: string  # folder name

  responses_received:     # Companies that replied
    - company: string
      posting: string
      sentiment: enum     # positive | neutral | negative
      summary: string

  interviews_detected:    # Scheduling emails found
    - company: string
      posting: string
      date: datetime
      added_to_prep: boolean

  offers_detected:        # Offer emails (URGENT)
    - company: string
      posting: string

  rejections_detected:
    - company: string
      posting: string

  unclassified:          # Couldn't auto-process, review manually
    - subject: string
      from: string
      date: datetime
```

---

## Event Types (additions to schema)

Add to posting _schema.yaml:

```yaml
# type: recruiter_inbound
# When: Recruiter reached out to you (not you applying)
data:
  recruiter_name: string
  recruiter_email: string
  channel: enum           # linkedin | email | other
  message_snippet: string # First 200 chars
  email_id: string        # Gmail message ID for reference

# type: application_confirmed
# When: ATS confirmation email received
data:
  confirmation_email_id: string
  confirmed_at: datetime
```

---

## Security Notes

1. **Credentials in .gitignore** - Never commit OAuth tokens
2. **Read-only scope first** - `gmail.readonly` until we need to send
3. **Token refresh** - Agent handles token refresh automatically
4. **Audit log** - Log all email access in agent_run

---

## Implementation Steps

1. [ ] User: Create Google Cloud project, enable Gmail API
2. [ ] User: Create OAuth credentials, download credentials.json
3. [ ] User: Run initial auth to get gmail-tokens.json
4. [ ] Update .gitignore with credential files
5. [ ] Add Phase 0 to daily-agent.md
6. [ ] Update digest schema with email_scan section
7. [ ] Update posting schema with new event types
8. [ ] Test with a few emails manually
9. [ ] Enable in cron

---

## MCP Alternative

If there's a Gmail MCP server available, that might be simpler:

```bash
# Check for Gmail MCP
claude /mcp

# If available, configure in settings
```

MCP would handle OAuth flow and provide tools like:
- `gmail_search(query)`
- `gmail_read(message_id)`
- `gmail_list(label, max_results)`

This might be cleaner than raw API calls.
