#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python312Packages.gspread python312Packages.google-auth-oauthlib

import gspread
import pickle
import json

TOKEN_PATH = "/home/blyons/token.pickle"
SHEET_ID = "1mguJ97pk7h4o-ogcaWrhxKnPPcZfXZcmEiyL5n22--k"

with open(TOKEN_PATH, 'rb') as token:
    creds = pickle.load(token)

gc = gspread.authorize(creds)
spreadsheet = gc.open_by_key(SHEET_ID)

# Get full sheet metadata
metadata = spreadsheet.fetch_sheet_metadata()

for sheet in metadata['sheets']:
    if sheet['properties']['title'] == 'OSINT':
        print("OSINT Sheet - All Conditional Format Rules:\n")

        if 'conditionalFormats' in sheet:
            for i, rule in enumerate(sheet['conditionalFormats']):
                # Check all ranges in this rule
                for range_spec in rule.get('ranges', []):
                    start_col = range_spec.get('startColumnIndex', -1)
                    end_col = range_spec.get('endColumnIndex', -1)

                    # Check if it includes column D (index 3)
                    if start_col <= 3 < end_col:
                        print(f"\n{'='*70}")
                        print(f"Rule {i + 1} - Includes Column D (Answer Status)")
                        print(f"{'='*70}")
                        print(json.dumps(rule, indent=2))
                        break
        else:
            print("No conditional formatting rules found.")
