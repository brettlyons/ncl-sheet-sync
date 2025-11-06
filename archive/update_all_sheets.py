#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python312Packages.gspread python312Packages.google-auth-oauthlib python312Packages.requests

"""
Master script to update all NCL category sheets at once
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from update_sheet_template import (
    authenticate_gsheets,
    fetch_cyberskyline_data,
    parse_category_challenges,
    update_category_sheet
)

# All categories to update
CATEGORIES = [
    ("OSINT", "Open Source Intelligence"),
    ("Crypto", "Cryptography"),
    ("Cracking", "Password Cracking"),
    ("Log", "Log Analysis"),
    ("NTA", "Network Traffic Analysis"),
    ("Forensics", "Forensics"),
    ("Scanning", "Scanning & Reconnaissance"),
    ("Web", "Web Application Exploitation"),
    ("Enum and Exploit", "Enumeration & Exploitation")
]

def main():
    test_mode = '--test' in sys.argv
    dry_run = '--yes' not in sys.argv

    if dry_run:
        print("\n*** DRY RUN MODE ***")
        print("Use --yes flag to actually update the sheets\n")

    if test_mode:
        print("*** TEST MODE: Writing to rows 50+ ***\n")

    print("="*70)
    print("NCL Sheet Updater - All Categories")
    print("="*70)

    print("\nFetching data from cyberskyline...")
    preload_data = fetch_cyberskyline_data()

    print("Authenticating with Google Sheets...")
    gc = authenticate_gsheets()

    results = []

    for sheet_name, category_name in CATEGORIES:
        print(f"\n{'#'*70}")
        print(f"# Processing: {sheet_name}")
        print(f"{'#'*70}")

        print(f"Parsing {category_name} challenges...")
        challenges = parse_category_challenges(preload_data, category_name)

        if not challenges:
            print(f"WARNING: No challenges found for {category_name}")
            results.append((sheet_name, False, "No challenges found"))
            continue

        print(f"Found {len(challenges)} challenges with {sum(len(c['questions']) for c in challenges)} total questions")

        if not dry_run:
            try:
                success = update_category_sheet(gc, sheet_name, challenges, test_mode)
                results.append((sheet_name, success, "Success" if success else "Failed"))
            except Exception as e:
                print(f"ERROR updating {sheet_name}: {e}")
                results.append((sheet_name, False, str(e)))
        else:
            print(f"[DRY RUN] Would update {sheet_name} with {len(challenges)} challenges")
            results.append((sheet_name, True, "Dry run"))

    # Print summary
    print(f"\n{'='*70}")
    print("Summary")
    print(f"{'='*70}\n")

    for sheet_name, success, message in results:
        status = "✓" if success else "✗"
        print(f"  {status} {sheet_name:20s}: {message}")

    successful = sum(1 for _, success, _ in results if success)
    total = len(results)

    print(f"\n{successful}/{total} sheets updated successfully")

    if dry_run:
        print("\nTo actually update the sheets, run with --yes flag:")
        print("  ./update_all_sheets.py --yes")
        if not test_mode:
            print("\nTo test on empty rows first, use --test:")
            print("  ./update_all_sheets.py --test --yes")

    return 0 if successful == total else 1

if __name__ == "__main__":
    exit(main())
