#!/usr/bin/env python3
"""
Automated setup for NCL Sheet Sync
Auto-detects browser, extracts cookies, and configures config.py

Works on Linux, Windows, and macOS with Firefox, Chrome, Chromium, Brave, and Edge

Usage:
    python utils/auto_setup.py
"""

import sqlite3
import shutil
import os
import sys
import glob
import platform
import json
import base64
from pathlib import Path

# Try to import platform-specific decryption libraries
try:
    if platform.system() == "Windows":
        import win32crypt
        HAS_WIN32CRYPT = True
    else:
        HAS_WIN32CRYPT = False
except ImportError:
    HAS_WIN32CRYPT = False

try:
    from Crypto.Cipher import AES
    from Crypto.Protocol.KDF import PBKDF2
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def get_browser_paths():
    """Get cookie database paths for all major browsers on current OS"""
    system = platform.system()
    home = str(Path.home())

    paths = {}

    if system == "Linux":
        paths = {
            "Firefox": glob.glob(os.path.join(home, ".mozilla/firefox/*.default*/cookies.sqlite")),
            "Chrome": [os.path.join(home, ".config/google-chrome/Default/Cookies")],
            "Chromium": [os.path.join(home, ".config/chromium/Default/Cookies")],
            "Brave": [os.path.join(home, ".config/BraveSoftware/Brave-Browser/Default/Cookies")],
        }
    elif system == "Darwin":  # macOS
        paths = {
            "Firefox": glob.glob(os.path.join(home, "Library/Application Support/Firefox/Profiles/*.default*/cookies.sqlite")),
            "Chrome": [os.path.join(home, "Library/Application Support/Google/Chrome/Default/Cookies")],
            "Brave": [os.path.join(home, "Library/Application Support/BraveSoftware/Brave-Browser/Default/Cookies")],
            "Edge": [os.path.join(home, "Library/Application Support/Microsoft Edge/Default/Cookies")],
        }
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        localappdata = os.environ.get("LOCALAPPDATA", "")
        paths = {
            "Firefox": glob.glob(os.path.join(appdata, "Mozilla/Firefox/Profiles/*.default*/cookies.sqlite")),
            "Chrome": [os.path.join(localappdata, "Google/Chrome/User Data/Default/Network/Cookies")],
            "Edge": [os.path.join(localappdata, "Microsoft/Edge/User Data/Default/Network/Cookies")],
            "Brave": [os.path.join(localappdata, "BraveSoftware/Brave-Browser/User Data/Default/Network/Cookies")],
        }

    # Filter out non-existent paths
    return {browser: [p for p in paths_list if os.path.exists(p)]
            for browser, paths_list in paths.items() if paths_list}


def decrypt_chrome_cookie_windows(encrypted_value):
    """Decrypt Chrome cookie on Windows using DPAPI"""
    if not HAS_WIN32CRYPT:
        return None
    try:
        return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode('utf-8')
    except:
        return None


def get_chrome_key_linux():
    """Get Chrome's encryption key on Linux"""
    # Chrome v80+ stores encrypted key in Local State file
    system = platform.system()
    home = str(Path.home())

    if system == "Linux":
        local_state_paths = [
            os.path.join(home, ".config/google-chrome/Local State"),
            os.path.join(home, ".config/chromium/Local State"),
            os.path.join(home, ".config/BraveSoftware/Brave-Browser/Local State"),
        ]
    elif system == "Darwin":
        local_state_paths = [
            os.path.join(home, "Library/Application Support/Google/Chrome/Local State"),
            os.path.join(home, "Library/Application Support/BraveSoftware/Brave-Browser/Local State"),
        ]
    else:
        return None

    for path in local_state_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    local_state = json.load(f)
                encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
                # Remove 'DPAPI' prefix on Windows, or just use the key
                encrypted_key = encrypted_key[5:]  # Remove b'DPAPI' prefix

                if system == "Linux":
                    # On Linux, derive key from password 'peanuts' (Chrome's default)
                    return PBKDF2(b'peanuts', b'saltysalt', dkLen=16, count=1)
                else:
                    return encrypted_key
            except:
                pass

    # Fallback for older Chrome versions on Linux
    if system == "Linux" and HAS_CRYPTO:
        return PBKDF2(b'peanuts', b'saltysalt', dkLen=16, count=1)

    return None


def decrypt_chrome_cookie_linux(encrypted_value, key):
    """Decrypt Chrome cookie on Linux using AES"""
    if not HAS_CRYPTO or not key:
        return None
    try:
        # Chrome v80+ uses AES-128-CBC with prefix 'v10' or 'v11'
        if encrypted_value[:3] == b'v10' or encrypted_value[:3] == b'v11':
            encrypted_value = encrypted_value[3:]
            iv = b' ' * 16  # Chrome uses 16 spaces as IV
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(encrypted_value)
            # Remove PKCS7 padding
            return decrypted[:-decrypted[-1]].decode('utf-8')
        else:
            # Older versions or different format
            return encrypted_value.decode('utf-8')
    except:
        return None


def extract_firefox_cookies(db_path):
    """Extract cookies from Firefox database"""
    try:
        # Make a temporary copy (Firefox locks the original)
        temp_db = "/tmp/firefox_cookies_copy.sqlite"
        shutil.copy2(db_path, temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, value FROM moz_cookies
            WHERE host LIKE '%cyberskyline.com%'
        """)
        cookies = cursor.fetchall()
        conn.close()
        os.remove(temp_db)

        if cookies:
            return "; ".join([f"{name}={value}" for name, value in cookies])
    except Exception as e:
        print(f"  Error extracting Firefox cookies: {e}")
    return None


def extract_chrome_cookies(db_path, browser_name):
    """Extract cookies from Chrome-based browser"""
    try:
        # Make a temporary copy
        temp_db = f"/tmp/{browser_name.lower()}_cookies_copy.sqlite"
        shutil.copy2(db_path, temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Chrome/Chromium cookie schema
        cursor.execute("""
            SELECT name, value, encrypted_value FROM cookies
            WHERE host_key LIKE '%cyberskyline.com%'
        """)
        cookies = cursor.fetchall()
        conn.close()
        os.remove(temp_db)

        if not cookies:
            return None

        # Decrypt cookies if needed
        system = platform.system()
        cookie_list = []

        for name, value, encrypted_value in cookies:
            # Try plaintext value first
            if value:
                cookie_list.append(f"{name}={value}")
            elif encrypted_value:
                # Try to decrypt
                decrypted = None

                if system == "Windows":
                    decrypted = decrypt_chrome_cookie_windows(encrypted_value)
                elif system in ["Linux", "Darwin"]:
                    key = get_chrome_key_linux()
                    decrypted = decrypt_chrome_cookie_linux(encrypted_value, key)

                if decrypted:
                    cookie_list.append(f"{name}={decrypted}")
                else:
                    print(f"  Warning: Could not decrypt cookie '{name}'")

        if cookie_list:
            return "; ".join(cookie_list)
    except Exception as e:
        print(f"  Error extracting {browser_name} cookies: {e}")
    return None


def find_and_extract_cookies():
    """Try all browsers and return first successful cookie extraction"""
    print("Detecting browsers and extracting cookies...")
    print()

    browser_paths = get_browser_paths()

    if not browser_paths:
        print("ERROR: No supported browsers found!")
        print("Supported browsers: Firefox, Chrome, Chromium, Brave, Edge")
        return None, None

    print(f"Found browsers: {', '.join(browser_paths.keys())}")
    print()

    for browser, paths in browser_paths.items():
        for db_path in paths:
            print(f"Trying {browser}: {db_path}")

            if browser == "Firefox":
                cookies = extract_firefox_cookies(db_path)
            else:
                cookies = extract_chrome_cookies(db_path, browser)

            if cookies:
                print(f"✓ Successfully extracted cookies from {browser}!")
                return cookies, browser
            else:
                print(f"  No cyberskyline.com cookies found")

    print()
    print("ERROR: No cyberskyline.com cookies found in any browser!")
    print("Make sure you're logged into cyberskyline.com in at least one browser.")
    return None, None


def update_or_create_config(cookie_file_path):
    """Update config.py or create from config.example.py"""
    home = str(Path.home())
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(script_dir, "config.py")
    example_path = os.path.join(script_dir, "config.example.py")

    # Check if config.py exists
    if os.path.exists(config_path):
        print(f"\nUpdating existing config.py...")

        # Read existing config
        with open(config_path, 'r') as f:
            lines = f.readlines()

        # Update COOKIE_FILE line
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith('COOKIE_FILE ='):
                lines[i] = f'COOKIE_FILE = "{cookie_file_path}"\n'
                updated = True
                break

        if updated:
            with open(config_path, 'w') as f:
                f.writelines(lines)
            print(f"✓ Updated COOKIE_FILE in config.py")
        else:
            print(f"  Warning: Could not find COOKIE_FILE line in config.py")
            print(f"  Please manually add: COOKIE_FILE = \"{cookie_file_path}\"")

    elif os.path.exists(example_path):
        print(f"\nCreating config.py from template...")

        # Read example config
        with open(example_path, 'r') as f:
            lines = f.readlines()

        # Update COOKIE_FILE line
        for i, line in enumerate(lines):
            if line.strip().startswith('COOKIE_FILE ='):
                lines[i] = f'COOKIE_FILE = "{cookie_file_path}"\n'
                break

        # Write new config.py
        with open(config_path, 'w') as f:
            f.writelines(lines)

        print(f"✓ Created config.py")
        print(f"✓ Set COOKIE_FILE to {cookie_file_path}")
        print()
        print("⚠ You still need to configure:")
        print("  - SHEET_ID (your Google Sheet ID)")
        print("  - CYBERSKYLINE_URL (your NCL world URL)")
        print("  - TOKEN_PATH (run utils/setup_google_auth.py first)")
    else:
        print(f"\nERROR: config.example.py not found!")
        print(f"Cannot create config.py automatically.")
        return False

    return True


def main():
    print("="*70)
    print("NCL Sheet Sync - Automated Setup")
    print("="*70)
    print()

    # Extract cookies
    cookies, browser = find_and_extract_cookies()

    if not cookies:
        print()
        print("Please log into cyberskyline.com in your browser and try again.")
        return 1

    # Save cookies to file
    home = str(Path.home())
    cookie_file = os.path.join(home, "cyberskyline_cookies.txt")

    with open(cookie_file, 'w') as f:
        f.write(cookies)

    print()
    print(f"✓ Saved cookies to: {cookie_file}")

    # Update or create config.py
    if update_or_create_config(cookie_file):
        print()
        print("="*70)
        print("Setup Complete!")
        print("="*70)
        print()
        print("Next steps:")
        print("1. Run utils/setup_google_auth.py for Google Sheets authentication")
        print("2. Edit config.py and fill in:")
        print("   - SHEET_ID")
        print("   - CYBERSKYLINE_URL")
        print("   - TOKEN_PATH (from step 1)")
        print()
        print("Then test with: ./update_sheet.py osint")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
