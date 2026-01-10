#!/usr/bin/env python3
"""
LinkedIn archive tools for the agent.

Usage:
  linkedin-tools.py connections [--company COMPANY] [--json]
  linkedin-tools.py skills
  linkedin-tools.py past-applications
  linkedin-tools.py companies-followed

Examples:
  linkedin-tools.py connections --company "Acme Corp"  # Find referrals at company
  linkedin-tools.py connections --json                  # All connections as JSON
  linkedin-tools.py past-applications                   # Companies you've applied to
"""

import os
import sys
import csv
import json
import argparse
import yaml
from pathlib import Path

def find_archive_dir():
    """Find LinkedIn archive directory in multiple locations."""
    script_repo = Path(__file__).parent.parent
    cwd = Path.cwd()
    data_dir = Path(os.environ.get('JOB_SEARCH_DATA', ''))

    search_paths = [
        data_dir / "linkedin_archive" if data_dir.is_dir() else None,
        cwd / "linkedin_archive",
        script_repo / "linkedin_archive",
    ]

    for path in search_paths:
        if path and path.is_dir():
            return path
    return script_repo / "linkedin_archive"  # Default fallback

def find_config_path():
    """Find config.yaml in multiple locations."""
    script_repo = Path(__file__).parent.parent
    cwd = Path.cwd()
    data_dir = Path(os.environ.get('JOB_SEARCH_DATA', ''))

    search_paths = [
        data_dir / "config.yaml" if data_dir.is_dir() else None,
        cwd / "config.yaml",
        script_repo / "config.yaml",
    ]

    for path in search_paths:
        if path and path.exists():
            return path
    return script_repo / "config.yaml"  # Default fallback

ARCHIVE_DIR = find_archive_dir()
CONFIG_PATH = find_config_path()

def load_config():
    """Load config.yaml for dynamic settings."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}

def get_linkedin_username():
    """Get LinkedIn username from config or environment."""
    config = load_config()
    # Check config first, then environment, then return None
    username = config.get('linkedin', {}).get('username')
    if not username:
        username = os.environ.get('LINKEDIN_USERNAME')
    return username

def load_csv(filename):
    """Load a CSV file from the archive, handling notes header."""
    filepath = ARCHIVE_DIR / filename
    if not filepath.exists():
        return []

    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    # Skip notes header if present (LinkedIn adds notes before actual CSV)
    lines = content.split('\n')
    header_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('First Name,') or line.startswith('Name') or line.startswith('Organization,') or line.startswith('Application Date,'):
            header_idx = i
            break

    # Parse from header onwards
    reader = csv.DictReader(lines[header_idx:])
    return list(reader)

def get_connections(company_filter=None, as_json=False):
    """Get connections, optionally filtered by company."""
    connections = load_csv("Connections.csv")

    if company_filter:
        company_lower = company_filter.lower()
        connections = [
            c for c in connections
            if c.get('Company', '').lower().find(company_lower) >= 0
        ]

    # Clean up and format
    results = []
    for c in connections:
        results.append({
            'name': f"{c.get('First Name', '')} {c.get('Last Name', '')}".strip(),
            'company': c.get('Company', ''),
            'position': c.get('Position', ''),
            'linkedin_url': c.get('URL', ''),
            'email': c.get('Email Address', ''),
            'connected_on': c.get('Connected On', '')
        })

    if as_json:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("No connections found.")
            return
        print(f"Found {len(results)} connection(s):\n")
        for c in results:
            print(f"  {c['name']}")
            print(f"    {c['position']} at {c['company']}")
            if c['email']:
                print(f"    Email: {c['email']}")
            print(f"    {c['linkedin_url']}")
            print()

def get_skills():
    """Get your LinkedIn skills."""
    skills = load_csv("Skills.csv")
    skill_names = [s.get('Name', '') for s in skills if s.get('Name')]
    print(json.dumps(skill_names, indent=2))

def get_past_applications():
    """Get companies you've already applied to via LinkedIn."""
    apps = load_csv("Jobs/Job Applications.csv")

    # Extract unique companies
    companies = {}
    for app in apps:
        company = app.get('Company Name', '').strip()
        if company and company not in companies:
            companies[company] = {
                'company': company,
                'last_applied': app.get('Application Date', ''),
                'role': app.get('Job Title', '')
            }

    results = list(companies.values())
    print(json.dumps(results, indent=2))

def get_companies_followed():
    """Get companies you follow on LinkedIn."""
    companies = load_csv("Company Follows.csv")
    results = [
        {
            'company': c.get('Organization', ''),
            'followed_on': c.get('Followed On', '')
        }
        for c in companies if c.get('Organization')
    ]
    print(json.dumps(results, indent=2))

def get_recruiters():
    """Get recruiters in your network."""
    connections = load_csv("Connections.csv")
    keywords = ['recruit', 'talent', 'staffing', 'hiring', 'sourcer']

    recruiters = []
    for c in connections:
        position = c.get('Position', '').lower()
        if any(kw in position for kw in keywords):
            recruiters.append({
                'name': f"{c.get('First Name', '')} {c.get('Last Name', '')}".strip(),
                'company': c.get('Company', ''),
                'position': c.get('Position', ''),
                'linkedin_url': c.get('URL', ''),
                'email': c.get('Email Address', '')
            })

    print(json.dumps(recruiters, indent=2))

def get_network_companies():
    """Get all companies where you have connections (for referral matching)."""
    connections = load_csv("Connections.csv")

    companies = {}
    for c in connections:
        company = c.get('Company', '').strip()
        if not company:
            continue
        if company not in companies:
            companies[company] = []
        companies[company].append({
            'name': f"{c.get('First Name', '')} {c.get('Last Name', '')}".strip(),
            'position': c.get('Position', ''),
            'linkedin_url': c.get('URL', '')
        })

    # Sort by connection count
    results = [
        {'company': k, 'connection_count': len(v), 'contacts': v}
        for k, v in sorted(companies.items(), key=lambda x: -len(x[1]))
    ]
    print(json.dumps(results, indent=2))

def get_recruiter_messages(days=None):
    """Get inbound recruiter messages (job opportunities)."""
    messages = load_csv("messages.csv")
    config = load_config()
    linkedin_username = get_linkedin_username()

    # Keywords indicating recruiter outreach - merge defaults with config
    default_keywords = ['hiring', 'role', 'opportunity', 'position', 'engineer',
                       'developer', 'salary', 'remote', 'looking for',
                       'your background', 'your profile']
    # Add target roles from config as keywords
    target_roles = config.get('search', {}).get('target_roles', [])
    role_keywords = [r.lower().split()[-1] for r in target_roles]  # e.g., "Platform Engineer" -> "engineer"
    job_keywords = list(set(default_keywords + role_keywords))

    recruiter_msgs = []
    seen_convos = set()

    for msg in messages:
        # Skip outgoing messages (from you)
        sender_url = msg.get('SENDER PROFILE URL', '').lower()
        if linkedin_username and linkedin_username.lower() in sender_url:
            continue

        # Skip sponsored/ads
        if msg.get('FROM', '') == 'LinkedIn Member':
            continue

        content = msg.get('CONTENT', '').lower()
        subject = msg.get('SUBJECT', '').lower()

        # Check if it looks like job outreach
        if not any(kw in content or kw in subject for kw in job_keywords):
            continue

        # Dedupe by conversation
        convo_id = msg.get('CONVERSATION ID', '')
        if convo_id in seen_convos:
            continue
        seen_convos.add(convo_id)

        # Parse salary if mentioned
        import re
        salary_match = re.search(r'\$(\d{2,3})[kK,]?\s*[-–to]+\s*\$?(\d{2,3})[kK]?', content)
        salary = None
        if salary_match:
            low, high = salary_match.groups()
            salary = f"${low}k-${high}k"

        recruiter_msgs.append({
            'date': msg.get('DATE', ''),
            'from': msg.get('FROM', ''),
            'from_url': msg.get('SENDER PROFILE URL', ''),
            'subject': msg.get('SUBJECT', '') or msg.get('CONVERSATION TITLE', ''),
            'snippet': msg.get('CONTENT', '')[:300].replace('\n', ' '),
            'salary': salary,
            'conversation_id': convo_id
        })

    # Sort by date descending
    recruiter_msgs.sort(key=lambda x: x['date'], reverse=True)

    print(json.dumps(recruiter_msgs, indent=2))

def get_message_stats():
    """Get statistics on LinkedIn messages for ROI tracking."""
    messages = load_csv("messages.csv")
    linkedin_username = get_linkedin_username()

    from collections import Counter
    from datetime import datetime

    inbound = []
    outbound = []

    for msg in messages:
        sender_url = msg.get('SENDER PROFILE URL', '').lower()
        if linkedin_username and linkedin_username.lower() in sender_url:
            outbound.append(msg)
        elif msg.get('FROM', '') != 'LinkedIn Member':
            inbound.append(msg)

    # Count by month
    def get_month(date_str):
        try:
            dt = datetime.strptime(date_str.split(' ')[0], '%Y-%m-%d')
            return dt.strftime('%Y-%m')
        except:
            return 'unknown'

    inbound_by_month = Counter(get_month(m.get('DATE', '')) for m in inbound)
    outbound_by_month = Counter(get_month(m.get('DATE', '')) for m in outbound)

    # Unique recruiters
    recruiters = set()
    for msg in inbound:
        sender = msg.get('FROM', '')
        url = msg.get('SENDER PROFILE URL', '')
        if sender and url:
            recruiters.add((sender, url))

    stats = {
        'total_messages': len(messages),
        'inbound': len(inbound),
        'outbound': len(outbound),
        'unique_recruiters_contacted_you': len(recruiters),
        'inbound_by_month': dict(sorted(inbound_by_month.items(), reverse=True)[:6]),
        'outbound_by_month': dict(sorted(outbound_by_month.items(), reverse=True)[:6]),
        'response_rate': round(len(outbound) / max(len(inbound), 1) * 100, 1)
    }

    print(json.dumps(stats, indent=2))

def main():
    parser = argparse.ArgumentParser(description='LinkedIn archive tools')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # connections command
    conn_parser = subparsers.add_parser('connections', help='Search connections')
    conn_parser.add_argument('--company', '-c', help='Filter by company name')
    conn_parser.add_argument('--json', action='store_true', help='Output as JSON')

    # skills command
    subparsers.add_parser('skills', help='List your skills')

    # past-applications command
    subparsers.add_parser('past-applications', help='Companies you applied to')

    # companies-followed command
    subparsers.add_parser('companies-followed', help='Companies you follow')

    # recruiters command
    subparsers.add_parser('recruiters', help='Recruiters in your network')

    # network-companies command
    subparsers.add_parser('network-companies', help='All companies with connections')

    # recruiter-messages command
    subparsers.add_parser('recruiter-messages', help='Inbound recruiter job opportunities')

    # message-stats command
    subparsers.add_parser('message-stats', help='Message statistics for ROI tracking')

    args = parser.parse_args()

    if args.command == 'connections':
        get_connections(args.company, args.json)
    elif args.command == 'skills':
        get_skills()
    elif args.command == 'past-applications':
        get_past_applications()
    elif args.command == 'companies-followed':
        get_companies_followed()
    elif args.command == 'recruiters':
        get_recruiters()
    elif args.command == 'network-companies':
        get_network_companies()
    elif args.command == 'recruiter-messages':
        get_recruiter_messages()
    elif args.command == 'message-stats':
        get_message_stats()

if __name__ == '__main__':
    main()
