#!/usr/bin/env python3
"""
Format digest YAML into email-ready markdown.

Usage:
  format-email.py [DATE]           # Format digest for DATE (default: today)
  format-email.py --output FILE    # Write to file instead of stdout

Examples:
  format-email.py                          # Today's digest to stdout
  format-email.py 2026-01-15               # Specific date
  format-email.py --output /tmp/email.md   # Write to file
"""

import os
import sys
import argparse
from datetime import date
from pathlib import Path

import yaml


def load_digest(digest_date: str) -> dict:
    """Load digest YAML file."""
    script_dir = Path(__file__).parent
    repo_dir = script_dir.parent
    digest_path = repo_dir / "digest" / f"{digest_date}.yaml"

    if not digest_path.exists():
        print(f"ERROR: Digest not found: {digest_path}", file=sys.stderr)
        sys.exit(1)

    with open(digest_path) as f:
        return yaml.safe_load(f)


def format_urgent(urgent: list) -> str:
    """Format urgent items."""
    if not urgent:
        return "No urgent items today"

    lines = []
    for item in urgent:
        lines.append(f"- **{item.get('type', 'Alert')}**: {item.get('company', 'Unknown')} - {item.get('action', 'Review needed')}")
    return "\n".join(lines)


def format_hot_table(hot: list) -> str:
    """Format hot opportunities as markdown table rows."""
    if not hot:
        return "| *No hot opportunities* | | | | | |"

    lines = []
    for opp in hot[:10]:  # Limit to top 10
        company = opp.get('company', 'Unknown')
        role = opp.get('role', 'Unknown')[:30]
        score = opp.get('score', '-')
        match = f"{opp.get('match_rate', '-')}%"
        salary = opp.get('salary_max')
        salary_str = f"${salary//1000}k" if salary else "-"
        action = opp.get('action', 'Review')[:20]
        lines.append(f"| {company} | {role} | {score} | {match} | {salary_str} | {action} |")
    return "\n".join(lines)


def format_outreach(outreach: dict) -> str:
    """Format outreach items."""
    items = []

    # Referrals
    for ref in outreach.get('referrals', []):
        items.append(f"- **Referral**: Contact {ref.get('contact', 'connection')} at {ref.get('company', 'company')}")

    # Follow-ups
    for fu in outreach.get('follow_ups', []):
        items.append(f"- **Follow up**: {fu.get('company', 'Unknown')} (applied {fu.get('days_ago', '?')} days ago)")

    # Thank yous
    for ty in outreach.get('thank_yous', []):
        items.append(f"- **Thank you**: Send to {ty.get('interviewer', 'interviewer')} at {ty.get('company', 'company')}")

    # New outreach from email scan
    return "\n".join(items) if items else "No outreach needed today"


def format_upcoming(prep: list, digest: dict) -> str:
    """Format upcoming interviews and prep items."""
    items = []

    # Interviews from prep zone
    for interview in prep:
        items.append(f"- **{interview.get('company', 'Unknown')}**: {interview.get('round', 'Interview')} on {interview.get('date', 'TBD')}")

    # Recruiter inbound to respond to
    for outreach in digest.get('email_scan', {}).get('new_outreach', []):
        items.append(f"- **Respond**: {outreach.get('from', 'Recruiter')} at {outreach.get('company', 'Unknown')} - {outreach.get('role', 'Role')}")

    return "\n".join(items) if items else "No upcoming items"


def count_pipeline(digest: dict) -> dict:
    """Count pipeline stats from digest."""
    stats = digest.get('insights', {}).get('your_stats', {})
    return {
        'pending': stats.get('total_active', 0),
        'applied': 0,  # Would need to count from postings
        'interviewing': 0,
        'offers': 0,
    }


def format_email(digest: dict, digest_date: str) -> str:
    """Format full email from digest."""

    # Load template
    script_dir = Path(__file__).parent
    template_path = script_dir / "email-template.md"

    with open(template_path) as f:
        template = f.read()

    # Extract data
    urgent = digest.get('urgent', [])
    hot = digest.get('hot', [])
    outreach = digest.get('outreach', {})
    prep = digest.get('prep', [])
    pipeline_alerts = digest.get('pipeline_alerts', {})
    email_scan = digest.get('email_scan', {})
    new_today = digest.get('new_today', {})
    learning = digest.get('learning', {})

    # Count stats
    pipeline = count_pipeline(digest)

    # Format each section
    formatted = template.format(
        date=digest_date,
        urgent_count=len(urgent),
        urgent_items=format_urgent(urgent),
        hot_count=len(hot),
        hot_table=format_hot_table(hot),
        outreach_items=format_outreach(outreach),
        stale_count=len(pipeline_alerts.get('going_stale', [])),
        issues_count=len(pipeline_alerts.get('posting_issues', [])),
        new_roles_count=len(pipeline_alerts.get('new_roles_found', [])),
        upcoming_items=format_upcoming(prep, digest),
        pending=pipeline['pending'],
        applied=pipeline['applied'],
        interviewing=pipeline['interviewing'],
        offers=pipeline['offers'],
        new_count=new_today.get('count', 0),
        rejections_count=len(email_scan.get('rejections_detected', [])),
        article_title=learning.get('article', {}).get('title', 'No article today'),
        article_summary=learning.get('article', {}).get('summary', '')[:200] if learning.get('article') else '',
    )

    return formatted


def get_subject(digest: dict, digest_date: str) -> str:
    """Generate email subject line."""
    urgent = digest.get('urgent', [])
    if urgent:
        return f"🔥 [URGENT] Job Search: {len(urgent)} items need attention"
    return f"📋 Daily Job Search Digest - {digest_date}"


def main():
    parser = argparse.ArgumentParser(description='Format digest as email')
    parser.add_argument('date', nargs='?', default=str(date.today()), help='Digest date (YYYY-MM-DD)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--subject', '-s', action='store_true', help='Print subject line only')

    args = parser.parse_args()

    digest = load_digest(args.date)

    if args.subject:
        print(get_subject(digest, args.date))
        return

    formatted = format_email(digest, args.date)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(formatted)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(formatted)


if __name__ == '__main__':
    main()
