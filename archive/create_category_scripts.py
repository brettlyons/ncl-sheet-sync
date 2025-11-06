#!/usr/bin/env python3

import os

categories = [
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

script_template = '''#!/usr/bin/env nix-shell
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

SHEET_NAME = "{sheet_name}"
CATEGORY_NAME = "{category_name}"

def main():
    test_mode = '--test' in sys.argv

    print(f"Fetching data from cyberskyline...")
    preload_data = fetch_cyberskyline_data()

    print(f"Parsing {{CATEGORY_NAME}} challenges...")
    challenges = parse_category_challenges(preload_data, CATEGORY_NAME)

    if not challenges:
        print(f"No challenges found for {{CATEGORY_NAME}}")
        return 1

    print(f"Found {{len(challenges)}} challenges with {{sum(len(c['questions']) for c in challenges)}} total questions\\n")

    print("Authenticating with Google Sheets...")
    gc = authenticate_gsheets()

    if '--yes' in sys.argv:
        success = update_category_sheet(gc, SHEET_NAME, challenges, test_mode)
        return 0 if success else 1
    else:
        print("\\nUse --yes flag to actually update the sheet")
        print("Preview only - no changes made.")
        return 0

if __name__ == "__main__":
    exit(main())
'''

for sheet_name, category_name in categories:
    filename = f"update_{sheet_name.lower().replace(' ', '_')}_sheet.py"

    with open(filename, 'w') as f:
        f.write(script_template.format(
            sheet_name=sheet_name,
            category_name=category_name
        ))

    os.chmod(filename, 0o755)
    print(f"Created {filename}")

print("\nAll category scripts created!")
