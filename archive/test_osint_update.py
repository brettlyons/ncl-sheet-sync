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

    # Get the template row (row 4) to copy formatting/dropdowns from
    print("Reading existing sheet structure to preserve formatting...")

    # Start from row 3 (after headers)
    current_row = 3
    updates = []

    # Track question rows for copying formatting later
    question_rows = []
    marker_rows = []

    for cluster in challenge_clusters:
        # Add challenge marker row
        print(f"Row {current_row}: Challenge marker '{cluster['name']}'")
        marker_rows.append(current_row)
        updates.append({
            'range': f'A{current_row}',
            'values': [[cluster['name']]]
        })

        current_row += 1

        # Add question rows
        for question in cluster['questions']:
            question_text = f"Question {question['index']}"
            print(f"  Row {current_row}: {question_text} - {question['points']} points")

            question_rows.append(current_row)

            # Update columns A and N
            updates.append({
                'range': f'A{current_row}',
                'values': [[question_text]]
            })
            updates.append({
                'range': f'D{current_row}',
                'values': [['N/A']]  # Default Answer Status
            })
            updates.append({
                'range': f'N{current_row}',
                'values': [[question['points']]]
            })

            # Set default values for team member columns (columns G-M)
            updates.append({
                'range': f'G{current_row}:M{current_row}',
                'values': [['Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing']]
            })

            current_row += 1

        # Add blank row after each challenge (except the last)
        # This creates the grey separator for the next challenge
        current_row += 1

    print(f"\n{'='*70}")
    print(f"Total rows to update: {current_row - 3}")
    print(f"{'='*70}\n")

    # Check for --yes flag
    import sys
    if '--yes' in sys.argv:
        print("Updating cell values...")
        # Batch update
        worksheet.batch_update(updates)

        print("Copying formatting and data validation from row 4 (template)...")
        # Copy formatting from row 4 to all question rows
        # This preserves dropdowns and other formatting
        for row_num in question_rows:
            # Copy entire row 4 format to this row
            source_range = f'4:4'
            destination_range = f'{row_num}:{row_num}'

            # Use the spreadsheet API to copy format
            try:
                worksheet.spreadsheet.values_batch_get([f'A4:M4'])
                # Copy format by duplicating the row format
                requests_list = [{
                    'copyPaste': {
                        'source': {
                            'sheetId': worksheet.id,
                            'startRowIndex': 3,  # Row 4 (0-indexed)
                            'endRowIndex': 4,
                            'startColumnIndex': 0,
                            'endColumnIndex': 14  # Columns A-N
                        },
                        'destination': {
                            'sheetId': worksheet.id,
                            'startRowIndex': row_num - 1,  # 0-indexed
                            'endRowIndex': row_num,
                            'startColumnIndex': 0,
                            'endColumnIndex': 14
                        },
                        'pasteType': 'PASTE_DATA_VALIDATION'
                    }
                }]

                worksheet.spreadsheet.batch_update({'requests': requests_list})
            except Exception as e:
                print(f"  Note: Could not copy formatting to row {row_num}: {e}")

        print("\n✓ OSINT sheet updated successfully!")
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
