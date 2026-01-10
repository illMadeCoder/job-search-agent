#!/usr/bin/env python3
"""Test Gmail API access - list recent emails."""

import os
import json
from glob import glob
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    token_files = sorted(glob('gmail-tokens-*.json'))
    if not token_files:
        print("No token files found. Run gmail-auth.py first.")
        return

    for token_file in token_files:
        print(f"\n{'='*50}")
        print(f"Testing: {token_file}")
        print('='*50)

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
            # Save refreshed token
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

        # Get profile
        profile = service.users().getProfile(userId='me').execute()
        print(f"Email: {profile['emailAddress']}")
        print(f"Total messages: {profile['messagesTotal']}")

        # List last 5 emails
        print("\nLast 5 emails:")
        results = service.users().messages().list(userId='me', maxResults=5).execute()
        messages = results.get('messages', [])

        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me', id=msg['id'], format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()

            headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
            print(f"  - {headers.get('From', 'Unknown')[:40]}")
            print(f"    {headers.get('Subject', 'No subject')[:60]}")
            print()

if __name__ == '__main__':
    main()
