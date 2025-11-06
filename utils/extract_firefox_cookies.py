#!/usr/bin/env python3
"""
Extract cyberskyline.com cookies from Firefox

Usage:
    Set FIREFOX_PROFILE environment variable, or edit the firefox_profile path below
    export FIREFOX_PROFILE=~/.mozilla/firefox/YOUR_PROFILE.default
    python extract_firefox_cookies.py
"""
import sqlite3
import shutil
import os
import sys
import glob

# Try to auto-detect Firefox profile
home = os.path.expanduser("~")
firefox_base = os.path.join(home, ".mozilla", "firefox")

# Check for environment variable first
firefox_profile = os.environ.get("FIREFOX_PROFILE")

# If not set, try to find a default profile
if not firefox_profile:
    profiles = glob.glob(os.path.join(firefox_base, "*.default*"))
    if profiles:
        firefox_profile = profiles[0]
        print(f"Auto-detected Firefox profile: {firefox_profile}")
    else:
        print("ERROR: Could not find Firefox profile")
        print(f"Please set FIREFOX_PROFILE environment variable:")
        print(f"  export FIREFOX_PROFILE=~/.mozilla/firefox/YOUR_PROFILE.default")
        print(f"\nAvailable profiles:")
        for p in glob.glob(os.path.join(firefox_base, "*")):
            if os.path.isdir(p):
                print(f"  {p}")
        sys.exit(1)

cookies_db = os.path.join(firefox_profile, "cookies.sqlite")

if not os.path.exists(cookies_db):
    print(f"ERROR: Cookie database not found at: {cookies_db}")
    sys.exit(1)

# Make a temporary copy (Firefox locks the original)
temp_cookies = "/tmp/cookies_copy.sqlite"
shutil.copy2(cookies_db, temp_cookies)

# Connect and extract cookies for cyberskyline.com
conn = sqlite3.connect(temp_cookies)
cursor = conn.cursor()

# Query cookies for cyberskyline.com
cursor.execute("""
    SELECT name, value, host, path
    FROM moz_cookies
    WHERE host LIKE '%cyberskyline.com%'
""")

cookies = cursor.fetchall()
conn.close()

# Format as curl cookie string
if cookies:
    cookie_str = "; ".join([f"{name}={value}" for name, value, host, path in cookies])
    print("\nCookie string for curl:")
    print(cookie_str)

    # Save to file for easy use
    output_file = os.path.join(home, "cyberskyline_cookies.txt")
    with open(output_file, "w") as f:
        f.write(cookie_str)
    print(f"\nSaved to: {output_file}")
    print(f"\nUpdate your config.py with:")
    print(f'COOKIE_FILE = "{output_file}"')
else:
    print("No cookies found for cyberskyline.com. Make sure you're logged in!")

# Clean up
os.remove(temp_cookies)
