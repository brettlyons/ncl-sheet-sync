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

# Also check another sheet to see if there's a pattern
for sheet_name in ['OSINT', 'Crypto', 'Cracking']:
    print(f"\n{'='*70}")
    print(f"Checking {sheet_name} - Column D Answer Status")
    print(f"{'='*70}\n")

    try:
        metadata = spreadsheet.fetch_sheet_metadata({'includeGridData': True})

        for sheet in metadata['sheets']:
            if sheet['properties']['title'] == sheet_name:
                grid_data = sheet.get('data', [{}])[0]
                row_data = grid_data.get('rowData', [])

                # Look through rows to find different Answer Status values
                values_found = {}

                for row_idx in range(3, min(25, len(row_data))):
                    row = row_data[row_idx]
                    values = row.get('values', [])

                    if len(values) > 3:
                        cell = values[3]  # Column D
                        value = cell.get('formattedValue', '')

                        if value and value not in values_found:
                            fmt = cell.get('effectiveFormat', {})
                            bg = fmt.get('backgroundColor', {})

                            values_found[value] = bg

                            print(f'"{value}": {bg}')

                if not values_found:
                    print("No Answer Status values found")

    except Exception as e:
        print(f"Error: {e}")
