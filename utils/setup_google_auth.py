#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python312Packages.gspread python312Packages.google-auth-oauthlib

"""
Google Sheets OAuth2 Authentication Setup

This script helps you authenticate with Google Sheets API and create token.pickle.

Prerequisites:
1. Download OAuth2 credentials from Google Cloud Console
2. Save as 'credentials.json' in this directory
3. Run this script to authenticate
"""

from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
import os

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def main():
    if not os.path.exists('credentials.json'):
        print("ERROR: credentials.json not found!")
        print("\nPlease follow these steps:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create/select a project")
        print("3. Enable Google Sheets API")
        print("4. Create OAuth 2.0 credentials (Desktop app)")
        print("5. Download credentials.json to this directory")
        return

    print("Starting OAuth2 authentication flow...")
    print("A browser window will open for you to authorize access.\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

    print("\n✓ Authentication successful!")
    print(f"✓ token.pickle created at: {os.path.abspath('token.pickle')}")
    print("\nNext steps:")
    print(f"1. Update config.py with: TOKEN_PATH = '{os.path.abspath('token.pickle')}'")
    print("2. You can now delete credentials.json for security")

if __name__ == '__main__':
    main()
