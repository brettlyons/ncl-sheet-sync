#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python312Packages.gspread python312Packages.google-auth-oauthlib

import gspread
import pickle

TOKEN_PATH = "/home/blyons/token.pickle"
SHEET_ID = "1mguJ97pk7h4o-ogcaWrhxKnPPcZfXZcmEiyL5n22--k"

with open(TOKEN_PATH, 'rb') as token:
    creds = pickle.load(token)

gc = gspread.authorize(creds)
spreadsheet = gc.open_by_key(SHEET_ID)
worksheet = spreadsheet.worksheet("OSINT")

# Get the spreadsheet metadata to see data validation rules
sheet_metadata = spreadsheet.fetch_sheet_metadata()

# Find the OSINT sheet
for sheet in sheet_metadata['sheets']:
    if sheet['properties']['title'] == 'OSINT':
        print(f"OSINT Sheet ID: {sheet['properties']['sheetId']}")

        # Check if there are any data validation rules
        if 'data' in sheet:
            for grid_data in sheet.get('data', []):
                if 'rowData' in grid_data:
                    for i, row in enumerate(grid_data['rowData'][:10], 1):
                        if 'values' in row:
                            for j, cell in enumerate(row['values']):
                                if 'dataValidation' in cell:
                                    col_letter = chr(65 + j)  # A=65
                                    print(f"\nRow {i}, Column {col_letter}:")
                                    print(f"  Validation: {cell['dataValidation']}")
