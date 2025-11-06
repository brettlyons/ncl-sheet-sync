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

# Get full sheet metadata including validation
metadata = spreadsheet.fetch_sheet_metadata({'includeGridData': True})

for sheet in metadata['sheets']:
    if sheet['properties']['title'] == 'OSINT':
        grid_data = sheet.get('data', [{}])[0]
        row_data = grid_data.get('rowData', [])

        # Check row 4 (index 3)
        if len(row_data) > 3:
            row = row_data[3]
            values = row.get('values', [])

            print("Row 4 data validation rules:\n")

            for col_idx, cell in enumerate(values):
                if 'dataValidation' in cell:
                    col_letter = chr(65 + col_idx)  # A=65
                    print(f"Column {col_letter} (index {col_idx}):")
                    print(json.dumps(cell['dataValidation'], indent=2))
                    print()
