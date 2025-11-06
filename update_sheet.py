#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python312Packages.gspread python312Packages.google-auth-oauthlib python312Packages.requests

"""
Unified sheet updater - updates any category sheet or all sheets
Usage:
    ./update_sheet.py osint              # Preview OSINT sheet
    ./update_sheet.py osint --yes        # Update OSINT sheet
    ./update_sheet.py osint --test --yes # Update OSINT sheet (rows 50+)
    ./update_sheet.py all --yes          # Update all sheets
"""

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

# Category mappings
CATEGORIES = {
    "osint": ("OSINT", "Open Source Intelligence"),
    "crypto": ("Crypto", "Cryptography"),
    "cracking": ("Cracking", "Password Cracking"),
    "log": ("Log", "Log Analysis"),
    "nta": ("NTA", "Network Traffic Analysis"),
    "forensics": ("Forensics", "Forensics"),
    "scanning": ("Scanning", "Scanning & Reconnaissance"),
    "web": ("Web", "Web Application Exploitation"),
    "enum": ("Enum and Exploit", "Enumeration & Exploitation"),
}

def show_usage():
    """Show usage information"""
    print("Usage: ./update_sheet.py <category> [--test] [--yes]")
    print("\nAvailable categories:")
    for key, (sheet_name, category_name) in CATEGORIES.items():
        print(f"  {key:12s} - {category_name}")
    print(f"  {'all':12s} - Update all category sheets")
    print("\nFlags:")
    print("  --test    Write to rows 50+ instead of rows 3+ (for testing)")
    print("  --yes     Actually update the sheet (without this, just preview)")
    print("\nExamples:")
    print("  ./update_sheet.py osint              # Preview OSINT")
    print("  ./update_sheet.py osint --yes        # Update OSINT")
    print("  ./update_sheet.py all --yes          # Update all sheets")

def update_single_category(category_key, test_mode=False, dry_run=True):
    """Update a single category sheet"""
    if category_key not in CATEGORIES:
        print(f"ERROR: Unknown category '{category_key}'")
        print(f"Available: {', '.join(CATEGORIES.keys())}")
        return False

    sheet_name, category_name = CATEGORIES[category_key]

    print(f"Fetching data from cyberskyline...")
    preload_data = fetch_cyberskyline_data()

    print(f"Parsing {category_name} challenges...")
    challenges = parse_category_challenges(preload_data, category_name)

    if not challenges:
        print(f"No challenges found for {category_name}")
        return False

    print(f"Found {len(challenges)} challenges with {sum(len(c['questions']) for c in challenges)} total questions\n")

    if dry_run:
        print("\n*** DRY RUN MODE ***")
        print("Use --yes flag to actually update the sheet\n")
        print("Preview only - no changes made.")
        return True

    print("Authenticating with Google Sheets...")
    gc = authenticate_gsheets()

    success = update_category_sheet(gc, sheet_name, challenges, test_mode)
    return success

def update_all_categories(test_mode=False, dry_run=True):
    """Update all category sheets"""
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

    if not dry_run:
        print("Authenticating with Google Sheets...")
        gc = authenticate_gsheets()

    results = []

    for category_key, (sheet_name, category_name) in CATEGORIES.items():
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
        print("  ./update_sheet.py all --yes")
        if not test_mode:
            print("\nTo test on empty rows first, use --test:")
            print("  ./update_sheet.py all --test --yes")

    return successful == total

def main():
    # Check for help flags
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help', 'help']:
        show_usage()
        return 0 if len(sys.argv) > 1 else 1

    category = sys.argv[1].lower()
    test_mode = '--test' in sys.argv
    dry_run = '--yes' not in sys.argv

    if category == "all":
        success = update_all_categories(test_mode, dry_run)
        return 0 if success else 1
    else:
        success = update_single_category(category, test_mode, dry_run)
        return 0 if success else 1

if __name__ == "__main__":
    exit(main())
