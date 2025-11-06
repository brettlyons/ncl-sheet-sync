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

# Get full sheet metadata including formatting
metadata = spreadsheet.fetch_sheet_metadata({'includeGridData': True})

for sheet in metadata['sheets']:
    if sheet['properties']['title'] == 'OSINT':
        grid_data = sheet.get('data', [{}])[0]
        row_data = grid_data.get('rowData', [])

        # Check row 4 (index 3)
        if len(row_data) > 3:
            row = row_data[3]
            values = row.get('values', [])

            print("Row 4 cell formatting:\n")

            # Check specific columns with dropdowns
            cols_to_check = [3, 6, 7, 8, 9, 10, 11, 12]  # D, G, H, I, J, K, L, M

            for col_idx in cols_to_check:
                if col_idx < len(values):
                    cell = values[col_idx]
                    col_letter = chr(65 + col_idx)

                    print(f"\nColumn {col_letter} (index {col_idx}):")

                    if 'effectiveFormat' in cell:
                        fmt = cell['effectiveFormat']

                        if 'backgroundColor' in fmt:
                            print(f"  Background: {fmt['backgroundColor']}")

                        if 'textFormat' in fmt:
                            print(f"  Text format: {fmt['textFormat']}")

                        if 'borders' in fmt:
                            print(f"  Borders: {fmt['borders']}")
