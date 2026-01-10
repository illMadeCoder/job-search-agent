#!/usr/bin/env python3
"""
Gmail send utility for the agent.

Usage:
  gmail-send.py send --to EMAIL --subject SUBJECT --body BODY
  gmail-send.py send --to EMAIL --subject SUBJECT --body-file FILE
  gmail-send.py send --to EMAIL --subject SUBJECT --body BODY --html

Examples:
  gmail-send.py send --to me@example.com --subject "Daily Digest" --body-file digest.md
  gmail-send.py send --to me@example.com --subject "Urgent!" --body "Interview tomorrow"
"""

import os
import sys
import json
import argparse
import base64
from glob import glob
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


def get_service():
    """Get Gmail service using first available token."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(script_dir)
    cwd = os.getcwd()
    data_dir = os.environ.get('JOB_SEARCH_DATA', '')

    # Search order: env var > cwd > script's repo > data subdir
    search_paths = [
        os.path.join(data_dir, 'gmail-tokens-*.json') if data_dir else None,
        os.path.join(cwd, 'gmail-tokens-*.json'),
        os.path.join(repo_dir, 'gmail-tokens-*.json'),
        os.path.join(repo_dir, 'data', 'gmail-tokens-*.json'),
    ]
    search_paths = [p for p in search_paths if p]  # Remove None

    token_file = None
    for pattern in search_paths:
        files = sorted(glob(pattern))
        if files:
            token_file = files[0]
            break

    if not token_file:
        print("ERROR: No gmail-tokens-*.json found", file=sys.stderr)
        sys.exit(1)

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

    # Refresh if expired
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

    return build('gmail', 'v1', credentials=creds)


def send_email(to: str, subject: str, body: str, html: bool = False):
    """Send an email via Gmail API."""
    service = get_service()

    # Get sender email
    profile = service.users().getProfile(userId='me').execute()
    sender = profile['emailAddress']

    # Create message
    if html:
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(body, 'plain'))
        msg.attach(MIMEText(body, 'html'))
    else:
        msg = MIMEText(body)

    msg['to'] = to
    msg['from'] = sender
    msg['subject'] = subject

    # Encode and send
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        result = service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        print(json.dumps({
            'status': 'sent',
            'message_id': result['id'],
            'to': to,
            'subject': subject
        }))
        return True
    except Exception as e:
        print(json.dumps({
            'status': 'error',
            'error': str(e),
            'to': to,
            'subject': subject
        }))
        return False


def main():
    parser = argparse.ArgumentParser(description='Gmail send utility')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # send command
    send_parser = subparsers.add_parser('send', help='Send email')
    send_parser.add_argument('--to', required=True, help='Recipient email')
    send_parser.add_argument('--subject', required=True, help='Email subject')
    send_parser.add_argument('--body', help='Email body text')
    send_parser.add_argument('--body-file', help='Read body from file')
    send_parser.add_argument('--html', action='store_true', help='Send as HTML')

    args = parser.parse_args()

    if args.command == 'send':
        if args.body_file:
            with open(args.body_file) as f:
                body = f.read()
        elif args.body:
            body = args.body
        else:
            print("ERROR: Either --body or --body-file required", file=sys.stderr)
            sys.exit(1)

        success = send_email(args.to, args.subject, body, args.html)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
