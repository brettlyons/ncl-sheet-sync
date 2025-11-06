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
        print("OSINT Sheet - Checking for Answer Status (Column D) conditional formatting:\n")

        if 'conditionalFormats' in sheet:
            for i, rule in enumerate(sheet['conditionalFormats']):
                # Check if this rule applies to column D (index 3)
                for range_spec in rule.get('ranges', []):
                    start_col = range_spec.get('startColumnIndex', -1)
                    end_col = range_spec.get('endColumnIndex', -1)

                    # Column D is index 3
                    if start_col <= 3 < end_col:
                        print(f"\nRule {i + 1} (applies to column D):")
                        print(json.dumps(rule, indent=2))
                        break
