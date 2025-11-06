#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python312Packages.gspread python312Packages.google-auth-oauthlib python312Packages.requests

import gspread
from google.oauth2.credentials import Credentials
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

def authenticate_gsheets():
    """Authenticate with Google Sheets API"""
    with open(TOKEN_PATH, 'rb') as token:
        creds = pickle.load(token)
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
    match = re.search(r'window\.preload\s*=\s*({.*?});', response.text, re.DOTALL)
    preload_data = json.loads(match.group(1))
    return preload_data

def parse_osint_challenges(preload_data):
    """Parse OSINT challenge data"""
    modules = preload_data.get('report', {}).get('modules', [])

    for module in modules:
        if module['name'] == "Open Source Intelligence":
            challenge_clusters = []

            for cluster in module.get('clusters', []):
                cluster_name = cluster['name']
                num_questions = cluster['challenges']
                cluster_points = cluster['points']

                questions = []
                if num_questions > 0:
                    avg_points = cluster_points // num_questions

                    for i in range(num_questions):
                        if i == num_questions - 1:
                            points = cluster_points - (avg_points * (num_questions - 1))
                        else:
                            points = avg_points

                        questions.append({
                            'points': points,
                            'index': i + 1
                        })

                challenge_clusters.append({
                    'name': cluster_name,
                    'questions': questions,
                    'total_points': cluster_points
                })

            return challenge_clusters

    return []

def update_osint_sheet(gc, challenge_clusters):
    """Update the OSINT sheet, creating proper structure"""
    spreadsheet = gc.open_by_key(SHEET_ID)
    worksheet = spreadsheet.worksheet("OSINT")

    print(f"\n{'='*70}")
    print(f"Updating OSINT Sheet")
    print(f"{'='*70}\n")

    # Show what we're about to do
    print("Challenge structure from cyberskyline:")
    for i, cluster in enumerate(challenge_clusters, 1):
        print(f"  Challenge {i}: {cluster['name']}")
        print(f"    Questions: {len(cluster['questions'])}")
        print(f"    Total Points: {cluster['total_points']}")
        print(f"    Point distribution: {[q['points'] for q in cluster['questions']]}")
        print()

    # Step 1: Clear existing data (from row 3 onwards)
    print("Clearing existing data from row 3 onwards...")
    # Clear a large range to ensure we get everything
    worksheet.batch_clear(['A3:N100'])

    # Step 2: Build new data structure
    current_row = 3
    updates = []
    format_requests = []  # For formatting marker rows

    for cluster in challenge_clusters:
        marker_row = current_row

        # Add challenge marker row
        print(f"Row {current_row}: Challenge marker '{cluster['name']}'")
        updates.append({
            'range': f'A{current_row}',
            'values': [[cluster['name']]]
        })

        # Format this row with grey background
        format_requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': worksheet.id,
                    'startRowIndex': current_row - 1,  # 0-indexed
                    'endRowIndex': current_row,
                    'startColumnIndex': 0,
                    'endColumnIndex': 14  # Column N
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {
                            'red': 0.9,
                            'green': 0.9,
                            'blue': 0.9
                        }
                    }
                },
                'fields': 'userEnteredFormat.backgroundColor'
            }
        })

        current_row += 1

        # Add question rows
        for question in cluster['questions']:
            question_text = f"Question {question['index']}"
            print(f"  Row {current_row}: {question_text} - {question['points']} points")

            updates.append({
                'range': f'A{current_row}',
                'values': [[question_text]]
            })
            updates.append({
                'range': f'D{current_row}',  # Column D: Answer Status
                'values': [['N/A']]
            })
            updates.append({
                'range': f'N{current_row}',
                'values': [[question['points']]]
            })

            current_row += 1

        # Add blank row after each challenge (except maybe the last)
        current_row += 1

    print(f"\n{'='*70}")
    print(f"Total rows to update: {current_row - 3}")
    print(f"{'='*70}\n")

    # Step 3: Apply updates
    import sys
    if '--yes' in sys.argv:
        print("Applying updates...")
        worksheet.batch_update(updates)

        print("Applying formatting...")
        # Apply formatting via batch update
        body = {'requests': format_requests}
        spreadsheet.batch_update(body)

        print("\n✓ OSINT sheet updated successfully!")
        print(f"  - {len(challenge_clusters)} challenges")
        print(f"  - {sum(len(c['questions']) for c in challenge_clusters)} questions")
        print(f"  - Marker rows formatted with grey background")
    else:
        print("\nUse --yes flag to actually update the sheet")
        print("Preview only - no changes made.")

def main():
    print("Fetching data from cyberskyline...")
    preload_data = fetch_cyberskyline_data()

    print("Parsing OSINT challenges...")
    challenges = parse_osint_challenges(preload_data)

    print(f"Found {len(challenges)} challenges with {sum(len(c['questions']) for c in challenges)} total questions\n")

    print("Authenticating with Google Sheets...")
    gc = authenticate_gsheets()

    update_osint_sheet(gc, challenges)

    return 0

if __name__ == "__main__":
    exit(main())
