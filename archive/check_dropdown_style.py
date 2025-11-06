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
ss = gc.open_by_key(SHEET_ID)

# Get the raw API response with all fields for cell D4
spreadsheet_data = ss.fetch_sheet_metadata({
    'includeGridData': True,
    'ranges': ['OSINT!D4:D4']
})

for sheet in spreadsheet_data['sheets']:
    if sheet['properties']['title'] == 'OSINT':
        grid_data = sheet.get('data', [{}])[0]
        row_data = grid_data.get('rowData', [])

        if row_data and len(row_data) > 0:
            values = row_data[0].get('values', [])
            if values:
                cell = values[0]

                print("=== Complete cell D4 metadata ===")
                print(json.dumps(cell, indent=2))

                # Look specifically for dataValidation
                if 'dataValidation' in cell:
                    print("\n=== Data Validation structure ===")
                    print(json.dumps(cell['dataValidation'], indent=2))
