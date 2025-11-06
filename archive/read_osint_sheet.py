#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python312Packages.gspread python312Packages.google-auth-oauthlib

import gspread
from google.oauth2.credentials import Credentials
import os
import pickle

TOKEN_PATH = "/home/blyons/token.pickle"
SHEET_ID = "1mguJ97pk7h4o-ogcaWrhxKnPPcZfXZcmEiyL5n22--k"

with open(TOKEN_PATH, 'rb') as token:
    creds = pickle.load(token)

gc = gspread.authorize(creds)
spreadsheet = gc.open_by_key(SHEET_ID)
worksheet = spreadsheet.worksheet("OSINT")

# Get all values
all_values = worksheet.get_all_values()

print("OSINT Sheet Structure:\n")
print(f"{'Row':>4} | {'Column A (Question)':50s} | {'Column N (Points)':15s}")
print("-" * 75)

for i, row in enumerate(all_values[:30], 1):
    col_a = row[0] if len(row) > 0 else ""
    col_n = row[13] if len(row) > 13 else ""
    print(f"{i:4d} | {col_a:50s} | {col_n:15s}")
