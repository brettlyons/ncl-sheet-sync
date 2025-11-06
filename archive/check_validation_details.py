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

metadata = spreadsheet.fetch_sheet_metadata({'includeGridData': True})

for sheet in metadata['sheets']:
    if sheet['properties']['title'] == 'OSINT':
        grid_data = sheet.get('data', [{}])[0]
        row_data = grid_data.get('rowData', [])

        if len(row_data) > 3:
            row = row_data[3]
            values = row.get('values', [])

            # Check column D (index 3) - Answer Status
            if len(values) > 3:
                cell = values[3]
                if 'dataValidation' in cell:
                    print("Column D (Answer Status) - Full Data Validation:")
                    print(json.dumps(cell['dataValidation'], indent=2))
                    print()

            # Check column G (index 6) - Team member
            if len(values) > 6:
                cell = values[6]
                if 'dataValidation' in cell:
                    print("Column G (Team Member) - Full Data Validation:")
                    print(json.dumps(cell['dataValidation'], indent=2))
