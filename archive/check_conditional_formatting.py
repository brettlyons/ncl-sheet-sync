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
        print("OSINT Sheet - Conditional Format Rules:\n")

        if 'conditionalFormats' in sheet:
            for i, rule in enumerate(sheet['conditionalFormats']):
                print(f"\nRule {i + 1}:")
                print(json.dumps(rule, indent=2))
        else:
            print("No conditional formatting rules found.")
