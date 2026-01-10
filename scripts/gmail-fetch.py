#!/usr/bin/env python3
"""
Gmail fetch utility for the agent.

Usage:
  gmail-fetch.py list [--query QUERY] [--max N]    List emails
  gmail-fetch.py read MESSAGE_ID                    Read full email
  gmail-fetch.py accounts                           List configured accounts

Examples:
  gmail-fetch.py list --query "newer_than:1d" --max 20
  gmail-fetch.py list --query "from:linkedin.com newer_than:7d"
  gmail-fetch.py list --query "subject:interview newer_than:30d"
  gmail-fetch.py read 18d5a3b2c1f4e5d6
"""

import os
import sys
import json
import argparse
from glob import glob
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64
import re

def get_services():
    """Get Gmail service for each configured account."""
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    services = []
    for token_file in sorted(glob('gmail-tokens-*.json')):
        with open(token_file) as f:
            token_data = json.load(f)

        creds = Credentials(
            token=token_data['token'],
            refresh_token=token_data['refresh_token'],
            token_uri=token_data['token_uri'],
            client_id=token_data['client_id'],
            client_secret=token_data['client_secret'],
            scopes=token_data['scopes']
        )

        if creds.expired:
            creds.refresh(Request())
            with open(token_file, 'w') as f:
                json.dump({
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': list(creds.scopes)
                }, f, indent=2)

        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        services.append({
            'service': service,
            'email': profile['emailAddress'],
            'token_file': token_file
        })

    return services

def list_emails(query='newer_than:1d', max_results=20):
    """List emails matching query from all accounts."""
    services = get_services()
    all_emails = []

    for svc in services:
        service = svc['service']
        account = svc['email']

        try:
            results = service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
            messages = results.get('messages', [])

            for msg in messages:
                msg_data = service.users().messages().get(
                    userId='me', id=msg['id'], format='metadata',
                    metadataHeaders=['From', 'To', 'Subject', 'Date']
                ).execute()

                headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
                snippet = msg_data.get('snippet', '')[:200]

                all_emails.append({
                    'account': account,
                    'id': msg['id'],
                    'thread_id': msg['threadId'],
                    'date': headers.get('Date', ''),
                    'from': headers.get('From', ''),
                    'to': headers.get('To', ''),
                    'subject': headers.get('Subject', ''),
                    'snippet': snippet,
                    'labels': msg_data.get('labelIds', [])
                })
        except Exception as e:
            print(f"Error fetching from {account}: {e}", file=sys.stderr)

    # Sort by date (newest first)
    all_emails.sort(key=lambda x: x['date'], reverse=True)
    return all_emails

def read_email(message_id):
    """Read full email content by ID."""
    services = get_services()

    for svc in services:
        service = svc['service']
        account = svc['email']

        try:
            msg = service.users().messages().get(
                userId='me', id=message_id, format='full'
            ).execute()

            headers = {h['name']: h['value'] for h in msg['payload']['headers']}

            # Extract body
            body = ''
            if 'parts' in msg['payload']:
                for part in msg['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                            break
                    elif part['mimeType'] == 'text/html' and not body:
                        data = part['body'].get('data', '')
                        if data:
                            html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                            # Basic HTML stripping
                            body = re.sub(r'<[^>]+>', ' ', html)
                            body = re.sub(r'\s+', ' ', body).strip()
            else:
                data = msg['payload']['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

            return {
                'account': account,
                'id': message_id,
                'thread_id': msg['threadId'],
                'date': headers.get('Date', ''),
                'from': headers.get('From', ''),
                'to': headers.get('To', ''),
                'subject': headers.get('Subject', ''),
                'body': body[:5000],  # Limit body size
                'labels': msg.get('labelIds', [])
            }
        except Exception as e:
            continue  # Try next account

    return {'error': f'Message {message_id} not found'}

def list_accounts():
    """List configured Gmail accounts."""
    services = get_services()
    return [{'email': s['email'], 'token_file': s['token_file']} for s in services]

def main():
    parser = argparse.ArgumentParser(description='Gmail fetch utility')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # list command
    list_parser = subparsers.add_parser('list', help='List emails')
    list_parser.add_argument('--query', '-q', default='newer_than:1d', help='Gmail search query')
    list_parser.add_argument('--max', '-m', type=int, default=20, help='Max results')

    # read command
    read_parser = subparsers.add_parser('read', help='Read email by ID')
    read_parser.add_argument('message_id', help='Message ID')

    # accounts command
    subparsers.add_parser('accounts', help='List configured accounts')

    args = parser.parse_args()

    if args.command == 'list':
        emails = list_emails(args.query, args.max)
        print(json.dumps(emails, indent=2))
    elif args.command == 'read':
        email = read_email(args.message_id)
        print(json.dumps(email, indent=2))
    elif args.command == 'accounts':
        accounts = list_accounts()
        print(json.dumps(accounts, indent=2))

if __name__ == '__main__':
    main()
