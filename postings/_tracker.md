# Posting Tracker

## Needs Review (.review flag)

| Folder | Issue | Action Needed |
|--------|-------|---------------|
| | | |

## Pending Review (.pending_review)

| Folder | Created | Recommendation |
|--------|---------|----------------|
| | | |

## Applied (.applied)

| Folder | Applied | Expiry |
|--------|---------|--------|
| | | |

## Interviewing (.interviewing)

| Folder | Stage | Next Interview |
|--------|-------|----------------|
| | | |

## Closed (.offer / .rejected / .expired / .withdrawn)

| Folder | Outcome | Date |
|--------|---------|------|
| | | |

---

## Stats

- **Needs review**: 0
- **Pending review**: 0
- **Applied**: 0
- **Interviewing**: 0
- **Offers**: 0
- **Rejected**: 0
- **Expired**: 0
- **Withdrawn**: 0

---

## Folder Naming Convention

```
{company}.{role}.{state}.{YYYY-MM-DDTHHMM}Z/
```

Examples:
- `acme-corp.platform-engineer.pending_review.2026-01-10T0400Z/`
- `datadog.sre.applied.2026-01-10T0500Z/`
- `stripe.devops-engineer.applied.review.2026-01-09T0400Z/`

**Timestamp**: Last health check time (UTC)

**States**: `pending_review`, `applied`, `interviewing`, `offer`, `rejected`, `expired`, `withdrawn`

**`.review` suffix**: Needs attention (posting missing or new roles found)
