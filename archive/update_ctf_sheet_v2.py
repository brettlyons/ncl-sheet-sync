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
    """Parse challenge data into structured format organized by challenge clusters"""
    challenges_by_category = {}

    modules = preload_data.get('report', {}).get('modules', [])

    for module in modules:
        category_name = module['name']
        sheet_name = CATEGORY_MAP.get(category_name, category_name)

        challenge_clusters = []

        # Each module has clusters (challenges)
        for cluster in module.get('clusters', []):
            cluster_name = cluster['name']
            num_questions = cluster['challenges']  # Note: 'challenges' in JSON = questions
            cluster_points = cluster['points']

            # Create question list for this challenge cluster
            questions = []
            if num_questions > 0:
                avg_points = cluster_points // num_questions

                for i in range(num_questions):
                    # Calculate points (last question gets remainder)
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

        challenges_by_category[sheet_name] = challenge_clusters

    return challenges_by_category

def find_challenge_markers(worksheet):
    """Find the rows that are challenge markers (grey separator rows)"""
    all_values = worksheet.get_all_values()

    markers = []
    current_row = 3  # Start after header rows (rows 1-2)

    while current_row <= len(all_values):
        row = all_values[current_row - 1] if current_row <= len(all_values) else []

        # Check if this is a marker row:
        # - Either has text in column A (challenge name)
        # - Or is empty in both column A and column N (blank separator)
        col_a = row[0] if len(row) > 0 else ""
        col_n = row[13] if len(row) > 13 else ""

        # If this row has no point value in column N, it's likely a marker
        if col_n == "" or col_n == "Point Value":
            # Count how many question rows follow this marker
            question_count = 0
            check_row = current_row + 1

            while check_row <= len(all_values):
                check_row_data = all_values[check_row - 1] if check_row <= len(all_values) else []
                check_col_n = check_row_data[13] if len(check_row_data) > 13 else ""

                # If we hit another row with no points, it's the next marker
                if check_col_n == "" or check_col_n == "Point Value":
                    break

                question_count += 1
                check_row += 1

            markers.append({
                'row': current_row,
                'name': col_a,
                'question_count': question_count
            })

            current_row = check_row
        else:
            current_row += 1

    return markers

def update_sheet(gc, challenges_by_category, dry_run=False):
    """Update the Google Sheet with challenge data"""
    spreadsheet = gc.open_by_key(SHEET_ID)

    print(f"\n{'='*70}")
    print(f"Updating sheet: {spreadsheet.title}")
    print(f"{'='*70}\n")

    for sheet_name, challenge_clusters in challenges_by_category.items():
        print(f"\nProcessing: {sheet_name}")
        print(f"  Found {len(challenge_clusters)} challenge clusters")

        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"  WARNING: Sheet '{sheet_name}' not found, skipping")
            continue

        # Find existing challenge marker rows
        markers = find_challenge_markers(worksheet)

        print(f"  Found {len(markers)} challenge markers in sheet")

        if len(markers) != len(challenge_clusters):
            print(f"  WARNING: Marker count ({len(markers)}) != cluster count ({len(challenge_clusters)})")
            print(f"  Will update as many as possible...")

        if dry_run:
            print("  DRY RUN - Would update:")
            for i, (marker, cluster) in enumerate(zip(markers, challenge_clusters)):
                print(f"    Row {marker['row']}: Challenge '{cluster['name']}'")
                print(f"      {len(cluster['questions'])} questions:")
                for j, q in enumerate(cluster['questions'][:3]):
                    print(f"        Row {marker['row'] + j + 1}: Question {q['index']} - {q['points']} pts")
                if len(cluster['questions']) > 3:
                    print(f"        ... and {len(cluster['questions']) - 3} more questions")
            continue

        # Prepare batch updates
        updates = []

        for marker, cluster in zip(markers, challenge_clusters):
            # Update challenge name in marker row
            updates.append({
                'range': f'A{marker["row"]}',
                'values': [[cluster['name']]]
            })

            # Update question rows
            for j, question in enumerate(cluster['questions']):
                question_row = marker['row'] + j + 1

                # Column A: Question text (for now just "Question N" since they're redacted)
                question_text = f"Question {question['index']}"

                # Column N: Point value
                updates.append({
                    'range': f'A{question_row}',
                    'values': [[question_text]]
                })
                updates.append({
                    'range': f'N{question_row}',
                    'values': [[question['points']]]
                })

        # Batch update
        if updates:
            worksheet.batch_update(updates)
            print(f"  ✓ Updated {len(challenge_clusters)} challenges")

    print(f"\n{'='*70}")
    print("Update complete!")
    print(f"{'='*70}\n")

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
    print(f"{'='*70}")
    for category, clusters in challenges.items():
        total_questions = sum(len(c['questions']) for c in clusters)
        total_points = sum(c['total_points'] for c in clusters)
        print(f"  {category:25s}: {len(clusters):2d} challenges, {total_questions:3d} questions, {total_points:4d} points")
    print(f"{'='*70}\n")

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
