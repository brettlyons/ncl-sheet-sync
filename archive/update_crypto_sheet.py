#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python312Packages.gspread python312Packages.google-auth-oauthlib python312Packages.requests

import sys
import os

# Add current directory to path to import template
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from update_sheet_template import (
    authenticate_gsheets,
    fetch_cyberskyline_data,
    parse_category_challenges,
    update_category_sheet
)

SHEET_NAME = "Crypto"
CATEGORY_NAME = "Cryptography"

def main():
    test_mode = '--test' in sys.argv

    print(f"Fetching data from cyberskyline...")
    preload_data = fetch_cyberskyline_data()

    print(f"Parsing {CATEGORY_NAME} challenges...")
    challenges = parse_category_challenges(preload_data, CATEGORY_NAME)

    if not challenges:
        print(f"No challenges found for {CATEGORY_NAME}")
        return 1

    print(f"Found {len(challenges)} challenges with {sum(len(c['questions']) for c in challenges)} total questions\n")

    print("Authenticating with Google Sheets...")
    gc = authenticate_gsheets()

    if '--yes' in sys.argv:
        success = update_category_sheet(gc, SHEET_NAME, challenges, test_mode)
        return 0 if success else 1
    else:
        print("\nUse --yes flag to actually update the sheet")
        print("Preview only - no changes made.")
        return 0

if __name__ == "__main__":
    exit(main())
