#!/usr/bin/env python3
"""Gmail OAuth authentication. Supports multiple accounts."""

import os
import sys
import json
from glob import glob
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = 'credentials.json'

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Find next available token number
    existing = glob('gmail-tokens-*.json')
    if existing:
        nums = [int(f.split('-')[-1].split('.')[0]) for f in existing]
        next_num = max(nums) + 1
    else:
        next_num = 1

    token_file = f'gmail-tokens-{next_num}.json'

    if not os.path.exists(CREDENTIALS_FILE):
        print(f"Missing {CREDENTIALS_FILE}")
        return

    print(f"Authenticating account #{next_num}")
    print("Opening browser - sign in with the email you want to add...")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=8080)

    with open(token_file, 'w') as f:
        json.dump({
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }, f, indent=2)

    print(f"\nSuccess! Tokens saved to {token_file}")

    # Show all configured accounts
    all_tokens = sorted(glob('gmail-tokens-*.json'))
    print(f"\nConfigured accounts: {len(all_tokens)}")
    for t in all_tokens:
        print(f"  - {t}")

if __name__ == '__main__':
    main()
