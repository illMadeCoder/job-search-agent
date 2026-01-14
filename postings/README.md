# Postings Directory

Each job opportunity is tracked as a folder containing a `posting.yaml` file.

## Folder Naming Convention

```
{company-slug}.{role-slug}.{state}.{YYYY-MM-DDTHHMM}Z/
  └── posting.yaml
```

**Examples:**
```
cloudflare.senior-platform-engineer.pending_review.2026-01-13T0500Z/
stripe.sre-infrastructure.applied.2026-01-10T1430Z/
discord.senior-sre.interviewing.2026-01-05T0900Z/
```

**Slugs:**
- Lowercase, hyphens for spaces
- Remove special characters
- Keep readable: `red-hat` not `redhat`, `included-health` not `includedhealth`

**Timestamp:** UTC time when folder was created (immutable)

---

## State Lifecycle

```
                                    ┌─────────────┐
                                    │   expired   │
                                    └──────▲──────┘
                                           │ 30 days no response
┌────────────────┐    ┌─────────┐    ┌─────┴──────┐    ┌───────────┐
│ pending_review │───►│ applied │───►│interviewing│───►│   offer   │
└───────┬────────┘    └────┬────┘    └─────┬──────┘    └───────────┘
        │                  │               │
        │                  │               │
        ▼                  ▼               ▼
   ┌─────────┐        ┌─────────┐    ┌──────────┐
   │withdrawn│        │withdrawn│    │ rejected │
   └─────────┘        └─────────┘    └──────────┘
```

### States

| State | Description | Next States |
|-------|-------------|-------------|
| `pending_review` | New opportunity, not yet applied | `applied`, `withdrawn` |
| `applied` | Application submitted | `interviewing`, `rejected`, `expired`, `withdrawn` |
| `interviewing` | Active interview process | `offer`, `rejected`, `withdrawn` |
| `offer` | Offer received | Terminal (outcome recorded in `posting.yaml`) |
| `rejected` | Company rejected (any stage) | Terminal |
| `expired` | 30 days since applied, no response | Terminal |
| `withdrawn` | You pulled out of process | Terminal |

### State Transitions

State changes are triggered by events and require **folder rename**:

```bash
# Example: Applied to a job
mv "company.role.pending_review.2026-01-13T0500Z" \
   "company.role.applied.2026-01-13T0500Z"
```

**Important:** The timestamp stays the same - only the state segment changes.

| Trigger | From | To | Folder Action |
|---------|------|----|----|
| User applies | `pending_review` | `applied` | Rename folder |
| Interview scheduled | `applied` | `interviewing` | Rename folder |
| Offer extended | `interviewing` | `offer` | Rename folder |
| Rejection email | any active | `rejected` | Rename folder |
| 30 days elapsed | `applied` | `expired` | Rename folder |
| User withdraws | any active | `withdrawn` | Rename folder |

---

## The `.review` Flag

Append `.review` suffix when a posting needs human attention:

```
company.role.applied.2026-01-13T0500Z.review/
```

**When to add `.review`:**
- Health check finds posting URL returns 404
- New roles found at same company
- Conflicting information detected
- Any anomaly requiring human decision

**Workflow:**
1. Agent adds `.review` suffix
2. Agent logs reason in `_tracker.md` under "Needs Review"
3. Human investigates and resolves
4. Human removes `.review` suffix

---

## Canonical Data Location

- **Current state**: Read from folder name (authoritative)
- **State history**: `posting.yaml → events[]` array
- **Application details**: `posting.yaml → application` section

The folder name IS the source of truth for current state. The `posting.yaml` file contains the full history and details.

---

## Files in Each Folder

| File | Purpose |
|------|---------|
| `posting.yaml` | All posting data (see `_schema.yaml`) |

Future additions may include:
- `cover_letter.md` - Generated cover letter
- `resume.pdf` - Tailored resume version
- `notes.md` - Freeform research notes

---

## Related Files

| File | Purpose |
|------|---------|
| `_schema.yaml` | YAML schema for `posting.yaml` |
| `_tracker.md` | Human-readable dashboard |
| `_priority_queue.yaml` | Ranked list for daily digest |
