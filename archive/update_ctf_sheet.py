#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python312Packages.gspread python312Packages.google-auth-oauthlib python312Packages.requests python312Packages.beautifulsoup4

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
import requests
import re
import json

# Configuration
SHEET_ID = "1mguJ97pk7h4o-ogcaWrhxKnPPcZfXZcmEiyL5n22--k"
CYBERSKYLINE_URL = "https://cyberskyline.com/world/684c235bdbe1ed8e2a7f7e72"
COOKIE_FILE = "/home/blyons/cyberskyline_cookies.txt"
TOKEN_PATH = "/home/blyons/token.pickle"

# Map cyberskyline category names to sheet tab names
CATEGORY_MAP = {
    "Open Source Intelligence": "OSINT",
    "Cryptography": "Crypto",
    "Password Cracking": "Cracking",
    "Log Analysis": "Log",
    "Network Traffic Analysis": "NTA",
    "Forensics": "Forensics",
    "Scanning & Reconnaissance": "Scanning",
    "Web Application Exploitation": "Web",
    "Enumeration & Exploitation": "Enum and Exploit"
}

def authenticate_gsheets():
    """Authenticate with Google Sheets API"""
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("ERROR: No valid credentials found. Run read_ctf_sheet.py first.")
            return None
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)

    return gspread.authorize(creds)

def fetch_cyberskyline_data():
    """Fetch challenge data from cyberskyline"""
    with open(COOKIE_FILE, 'r') as f:
        cookies_str = f.read().strip()

    headers = {
        'Cookie': cookies_str,
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0'
    }

    response = requests.get(CYBERSKYLINE_URL, headers=headers)

    if response.status_code != 200:
        print(f"ERROR: Failed to fetch page (status {response.status_code})")
        return None

    # Extract window.preload JSON from the HTML
    match = re.search(r'window\.preload\s*=\s*({.*?});', response.text, re.DOTALL)
    if not match:
        print("ERROR: Could not find preload data in page")
        return None

    try:
        preload_data = json.loads(match.group(1))
        return preload_data
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON: {e}")
        return None

def parse_challenges(preload_data):
    """Parse challenge data into a structured format"""
    challenges_by_category = {}

    # Get modules from the report section (has more detail)
    modules = preload_data.get('report', {}).get('modules', [])

    for module in modules:
        category_name = module['name']
        sheet_name = CATEGORY_MAP.get(category_name, category_name)

        challenges = []

        # Each module has clusters (challenge groups)
        for cluster in module.get('clusters', []):
            cluster_name = cluster['name']
            num_challenges = cluster['challenges']
            cluster_points = cluster['points']

            # If we have individual challenge details, use them
            # Otherwise, distribute points evenly across challenges
            if num_challenges > 0:
                avg_points = cluster_points // num_challenges

                for i in range(num_challenges):
                    challenge_name = f"{cluster_name} - Question {i+1}" if num_challenges > 1 else cluster_name
                    points = avg_points

                    # Adjust last challenge to account for rounding
                    if i == num_challenges - 1:
                        points = cluster_points - (avg_points * (num_challenges - 1))

                    challenges.append({
                        'name': challenge_name,
                        'points': points,
                        'cluster': cluster_name
                    })

        challenges_by_category[sheet_name] = challenges

    return challenges_by_category

def update_sheet(gc, challenges_by_category, dry_run=False):
    """Update the Google Sheet with challenge data"""
    spreadsheet = gc.open_by_key(SHEET_ID)

    print(f"\n{'='*60}")
    print(f"Updating sheet: {spreadsheet.title}")
    print(f"{'='*60}\n")

    for sheet_name, challenges in challenges_by_category.items():
        print(f"\nProcessing: {sheet_name}")
        print(f"  Found {len(challenges)} challenges")

        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"  WARNING: Sheet '{sheet_name}' not found, skipping")
            continue

        if dry_run:
            print("  DRY RUN - Would update:")
            for i, chal in enumerate(challenges[:5], 1):
                print(f"    Row {i+2}: {chal['name']} - {chal['points']} points")
            if len(challenges) > 5:
                print(f"    ... and {len(challenges) - 5} more")
            continue

        # Get current data to preserve existing values
        current_data = worksheet.get_all_values()

        # Starting from row 3 (row 1 is header, row 2 is column headers)
        start_row = 3

        # Prepare updates
        updates = []
        for i, challenge in enumerate(challenges):
            row_num = start_row + i

            # Column A: Question name
            # Column N (14): Point Value
            updates.append({
                'range': f'A{row_num}',
                'values': [[challenge['name']]]
            })
            updates.append({
                'range': f'N{row_num}',
                'values': [[challenge['points']]]
            })

        # Batch update
        if updates:
            worksheet.batch_update(updates)
            print(f"  ✓ Updated {len(challenges)} challenges")

    print(f"\n{'='*60}")
    print("Update complete!")
    print(f"{'='*60}\n")

def main():
    import sys
    dry_run = '--dry-run' in sys.argv

    print("Fetching data from cyberskyline...")
    preload_data = fetch_cyberskyline_data()

    if not preload_data:
        print("Failed to fetch data from cyberskyline")
        return 1

    print("Parsing challenge data...")
    challenges = parse_challenges(preload_data)

    # Show summary
    print("\nChallenge Summary:")
    print(f"{'='*60}")
    for category, chals in challenges.items():
        total_points = sum(c['points'] for c in chals)
        print(f"  {category:25s}: {len(chals):3d} challenges, {total_points:4d} points")
    print(f"{'='*60}\n")

    print("Authenticating with Google Sheets...")
    gc = authenticate_gsheets()

    if not gc:
        return 1

    if dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")

    update_sheet(gc, challenges, dry_run=dry_run)

    return 0

if __name__ == "__main__":
    exit(main())
