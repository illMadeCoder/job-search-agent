#!/usr/bin/env python3
"""
Gmail OAuth setup script.

Creates gmail-tokens-N.json files with read and send permissions.

Prerequisites:
1. Create a Google Cloud project at https://console.cloud.google.com
2. Enable Gmail API
3. Create OAuth 2.0 credentials (Desktop application)
4. Download credentials.json to this directory

Usage:
  gmail-oauth-setup.py              # Set up first account
  gmail-oauth-setup.py --account 2  # Set up second account
"""

import os
import sys
import json
import argparse
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
except ImportError:
    print("ERROR: Required packages not installed. Run:")
    print("  pip install google-auth-oauthlib google-api-python-client")
    sys.exit(1)

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
]


def find_credentials_file():
    """Find credentials.json in common locations."""
    script_dir = Path(__file__).parent
    repo_dir = script_dir.parent
    cwd = Path.cwd()

    search_paths = [
        cwd / "credentials.json",
        repo_dir / "credentials.json",
        script_dir / "credentials.json",
        Path.home() / "credentials.json",
    ]

    for path in search_paths:
        if path.exists():
            return path

    return None


def main():
    parser = argparse.ArgumentParser(description='Set up Gmail OAuth tokens')
    parser.add_argument('--account', '-a', type=int, default=1,
                        help='Account number (1, 2, etc.)')
    parser.add_argument('--credentials', '-c', type=str,
                        help='Path to credentials.json')
    args = parser.parse_args()

    if args.credentials:
        creds_path = Path(args.credentials)
    else:
        creds_path = find_credentials_file()

    if not creds_path or not creds_path.exists():
        print("ERROR: credentials.json not found")
        print()
        print("To create credentials:")
        print("1. Go to https://console.cloud.google.com")
        print("2. Create a new project (or select existing)")
        print("3. Enable the Gmail API:")
        print("   - APIs & Services > Library > Gmail API > Enable")
        print("4. Create OAuth credentials:")
        print("   - APIs & Services > Credentials > Create Credentials > OAuth client ID")
        print("   - Application type: Desktop app")
        print("   - Download the JSON file")
        print("5. Save as 'credentials.json' in current directory")
        sys.exit(1)

    print(f"Using credentials: {creds_path}")
    print(f"Setting up account #{args.account}")
    print()
    print("Scopes requested:")
    for scope in SCOPES:
        print(f"  - {scope.split('/')[-1]}")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)

    print("Opening browser for authentication...")
    print("(If browser doesn't open, check the terminal for a URL)")
    print()

    creds = flow.run_local_server(port=0)

    service = build('gmail', 'v1', credentials=creds)
    profile = service.users().getProfile(userId='me').execute()
    email = profile['emailAddress']

    print(f"Authenticated as: {email}")

    # Save token in repo root
    script_dir = Path(__file__).parent
    repo_dir = script_dir.parent
    token_file = repo_dir / f"gmail-tokens-{args.account}.json"

    token_data = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': list(creds.scopes)
    }

    with open(token_file, 'w') as f:
        json.dump(token_data, f, indent=2)

    print(f"Token saved to: {token_file}")
    print()
    print("Setup complete! You can now use gmail-fetch.py and gmail-send.py")

    print()
    print("Testing permissions...")
    try:
        if 'https://www.googleapis.com/auth/gmail.send' in creds.scopes:
            print("  ✓ Send permission granted")
        else:
            print("  ✗ Send permission NOT granted")

        if 'https://www.googleapis.com/auth/gmail.readonly' in creds.scopes:
            print("  ✓ Read permission granted")
        else:
            print("  ✗ Read permission NOT granted")
    except Exception as e:
        print(f"  Warning: Could not verify permissions: {e}")


if __name__ == '__main__':
    main()
