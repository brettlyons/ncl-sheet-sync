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

        print('Answer Status column (D) in existing rows:\n')

        for row_idx in range(3, min(10, len(row_data))):
            row = row_data[row_idx]
            values = row.get('values', [])

            if len(values) > 3:
                cell = values[3]  # Column D
                row_num = row_idx + 1

                value = cell.get('formattedValue', '')

                print(f'Row {row_num}: Value="{value}"')

                if 'effectiveFormat' in cell:
                    fmt = cell['effectiveFormat']
                    if 'backgroundColor' in fmt:
                        bg = fmt['backgroundColor']
                        print(f'  Background: {bg}')
                    if 'textFormat' in fmt:
                        tf = fmt.get('textFormat', {})
                        if 'foregroundColor' in tf:
                            print(f'  Text color: {tf["foregroundColor"]}')
