# NCL Sheet Sync

Automated tools for updating the SANS NCL Team Answer Sheet from cyberskyline.com data.

> **Note:** Built for a specific NCL team workflow. Documentation is functional but reflects organic development.

## Main Script

### Unified Updater
- `update_sheet.py` - Main script for updating any category or all sheets
  ```bash
  ./update_sheet.py osint              # Preview OSINT
  ./update_sheet.py osint --yes        # Update OSINT
  ./update_sheet.py all --yes          # Update all sheets
  ./update_sheet.py cracking --test --yes  # Test mode (rows 50+)
  ```

Available categories: `osint`, `crypto`, `cracking`, `log`, `nta`, `forensics`, `scanning`, `web`, `enum`, `all`

### Legacy Scripts (Optional)
Individual category scripts still available for convenience:
- `update_osint_sheet.py`, `update_crypto_sheet.py`, etc.
- `update_all_sheets.py`

These work the same as before but `update_sheet.py` is recommended.

## Usage

### Preview Changes (Dry Run)
```bash
cd ~/ncl-sheet-sync

# Preview single sheet
./update_sheet.py osint

# Preview all sheets
./update_sheet.py all
```

### Test Mode (Write to Empty Rows)
Tests on rows 50+ without touching existing data:
```bash
# Test single sheet
./update_sheet.py cracking --test --yes

# Test all sheets
./update_sheet.py all --test --yes
```

### Update Sheets
```bash
# Update single sheet
./update_sheet.py osint --yes

# Update all sheets
./update_sheet.py all --yes
```

## Features

Each script automatically:
- **Safety Check**: Before updating, checks if any work has been done (non-default dropdown values)
  - If work detected: Aborts update to prevent data loss
  - If safe: Clears old data and proceeds with update
- Fetches challenge data from cyberskyline.com
- Creates challenge marker rows (grey background)
- Populates question rows with:
  - Question names
  - Point values
  - Answer Status dropdown with color coding:
    - **Yes** = White text on green background
    - **No** = White text on red background
    - **N/A** = Black text on grey background (default)
    - **Needs Validation** = Black text on beige/yellow background
    - **Ready to submit** = Dark green text on light green background
  - Team member tracking dropdowns with color coding:
    - **Nothing** = White (invisible, default)
    - **Started** = Light green
    - **Agree** = Green, bold
    - **Disagree** = Red background, white bold text
    - **Surrender** = Black background, white bold text
- Applies borders and formatting

## Requirements

**Essential:**
- Logged into cyberskyline.com in a supported browser (Firefox, Chrome, Chromium, Brave, or Edge)
- Google Sheets OAuth2 credentials
- Python 3.8+ with required packages

**Supported Platforms:**
- Linux (tested on NixOS and Ubuntu)
- Windows 10/11
- macOS

## Setup

### Quick Start (Automated Setup)

The fastest way to get started:

```bash
# 1. Install Python dependencies (see "Installing Dependencies" below)

# 2. Run automated setup
python utils/auto_setup.py

# 3. Set up Google Sheets authentication
python utils/setup_google_auth.py

# 4. Edit config.py with your Sheet ID and World URL

# 5. Test it!
python update_sheet.py osint
```

**That's it!** The automated setup will detect your browser and extract cookies automatically.

---

### Installing Dependencies

#### Option A: Using Nix (Linux/macOS - Recommended for NixOS users)

If you have Nix installed, you get a reproducible environment with all dependencies:

```bash
cd ~/ncl-sheet-sync
nix-shell  # Drops you into a shell with everything installed
```

Or run scripts directly (they have nix-shell shebangs):
```bash
./update_sheet.py osint
```

**Note:** Nix is optional but provides isolated, reproducible environments. To install Nix, visit https://nixos.org/download.html

#### Option B: Using pip (Linux/Windows/macOS)

Install dependencies with pip:

```bash
pip install gspread google-auth-oauthlib requests pycryptodome
```

**Windows users:** For Chrome cookie decryption, also install:
```bash
pip install pywin32
```

#### Option C: Using system packages (Linux)

On Debian/Ubuntu:
```bash
sudo apt install python3-gspread python3-requests python3-crypto
```

On Fedora/RHEL:
```bash
sudo dnf install python3-gspread python3-requests python3-pycrypto
```

---

### Detailed Setup Steps

#### 1. Extract Cookies & Create Config

**Option A: Automated (Recommended)**

```bash
python utils/auto_setup.py
```

This will:
- Auto-detect your browser (Firefox, Chrome, Chromium, Brave, Edge)
- Extract cyberskyline.com cookies
- Create or update `config.py` with the cookie file path

**Option B: Manual (if automated setup fails)**

See manual instructions at the end of this section.

#### 2. Google Sheets Authentication

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Desktop app"
   - Download the credentials JSON file as `credentials.json`
5. Place `credentials.json` in the project directory
6. Run authentication script:
   ```bash
   python utils/setup_google_auth.py
   ```
   This will open a browser for OAuth authentication and create `token.pickle`.

#### 3. Configure Sheet and World URLs

Edit `config.py` and update:

```python
# Your Google Sheet ID (from the URL)
SHEET_ID = "your-sheet-id-here"

# Your NCL World URL
CYBERSKYLINE_URL = "https://cyberskyline.com/world/your-world-id"

# Token path (if setup_google_auth.py put it somewhere else)
TOKEN_PATH = "/path/to/token.pickle"
```

**Finding your Sheet ID:**
From your Google Sheet URL:
```
https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit
```

**Finding your World URL:**
1. Log into https://cyberskyline.com
2. Navigate to your NCL Gymnasium or Team Game
3. Copy the URL from your browser (format: `https://cyberskyline.com/world/...`)

**Note:** Use Gymnasium for testing. Switch to Team Game URL when competition starts.

### Verifying Setup

Test your configuration:
```bash
cd ~/ncl-sheet-sync
./update_sheet.py osint  # Dry run to test authentication
```

If you see challenge data, authentication is working!

### Cookie Maintenance

Cyberskyline session cookies expire periodically. If you get authentication errors:

1. Make sure you're logged into cyberskyline.com in your browser
2. Re-run `python utils/auto_setup.py` to refresh cookies
3. The script will automatically update your config

**Tip**: Session cookies typically last several hours to days. You may need to refresh them before each competition day.

---

### Manual Cookie Extraction (Troubleshooting)

If `auto_setup.py` doesn't work for your setup, you can extract cookies manually:

#### Firefox (Linux/macOS/Windows)

```bash
# Linux/macOS
sqlite3 ~/.mozilla/firefox/*.default*/cookies.sqlite \
  "SELECT name, value FROM moz_cookies WHERE host LIKE '%cyberskyline.com%'" \
  | awk -F'|' '{printf "%s=%s; ", $1, $2}' > ~/cyberskyline_cookies.txt

# Windows (PowerShell)
# Find your profile first:
dir $env:APPDATA\Mozilla\Firefox\Profiles\
# Then extract (replace YOUR_PROFILE):
sqlite3 "$env:APPDATA\Mozilla\Firefox\Profiles\YOUR_PROFILE.default\cookies.sqlite" "SELECT name, value FROM moz_cookies WHERE host LIKE '%cyberskyline.com%'" > cookies.txt
```

Or use the included helper script (Linux only):
```bash
python utils/extract_firefox_cookies.py
```

#### Chrome/Edge (Windows)

Chrome cookies are encrypted on Windows. You'll need a tool like:
- [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie) browser extension
- Export cookies for `cyberskyline.com` in Netscape format
- Convert to format: `name1=value1; name2=value2; ...`

#### Browser Extensions (All Platforms)

For any browser, you can use extensions like:
- **EditThisCookie** (Chrome/Edge)
- **Cookie-Editor** (Firefox/Chrome)

1. Install extension
2. Visit cyberskyline.com while logged in
3. Click extension icon
4. Export cookies for cyberskyline.com
5. Format as: `cookie1=value1; cookie2=value2; ...`
6. Save to `~/cyberskyline_cookies.txt`
7. Update `COOKIE_FILE` path in `config.py`

## Safety Mechanism

The scripts include a safety check to prevent accidental data loss:

- **Before updating**: Checks Answer Status (column D) and team member columns (G-M) for non-default values
- **If work detected**: Aborts with an error message to prevent overwriting your work
- **If safe**: Clears rows 3-100 and regenerates from cyberskyline data

### Overriding Safety Check

If you intentionally want to regenerate a sheet that has work in it:

1. Manually clear the data range (rows 3-100) in Google Sheets
2. Or manually reset dropdown values to defaults ("N/A" for Answer Status, "Nothing" for team members)
3. Then run the update script again

## For Competition Day

### Optimal Workflow

**IMPORTANT**: Run the updater **immediately** when the competition opens, before anyone starts working!

When the NCL Team Game starts:

1. **Before the game opens**: Make sure you're logged into cyberskyline.com in Firefox
2. **When challenges go live**: Run the updater immediately:
   ```bash
   cd ~/ncl-sheet-sync
   ./update_sheet.py all --yes
   ```
3. All 9 category sheets will be populated with actual challenge names and points
4. Team can now start working with the fully populated sheets

### Notes

- **Timing matters**: Run the update BEFORE anyone changes any dropdowns from their defaults
- **Data protection**: If any sheets already have work in them (non-default dropdown values), those sheets will be skipped to prevent data loss
- **Before competition**: If you run the scripts early, you'll only get "Redacted" placeholders. Wait until the game goes live for actual challenge data.
- **Cookie refresh**: Make sure your cyberskyline cookies are fresh (re-extract if needed)

## Files

### Configuration
- `config.example.py` - Template configuration file (commit to git)
- `config.py` - Your actual configuration (gitignored, create from example)
- `.gitignore` - Protects sensitive files from being committed
- `shell.nix` - Nix development environment with all dependencies

### Main Scripts
- `update_sheet.py` - Unified updater for single or all category sheets
- `update_sheet_template.py` - Core logic library

### Utilities (`utils/`)
- `auto_setup.py` - **Automated setup** - detects browser, extracts cookies, creates config.py (cross-platform)
- `setup_google_auth.py` - Google OAuth authentication setup
- `extract_firefox_cookies.py` - Manual Firefox cookie extraction (Linux-only, use auto_setup.py instead)

### Legacy Scripts (Optional)
- `update_all_sheets.py` - Alternative script to update all sheets
- `update_*_sheet.py` - Individual category updaters (9 files)

### Archive (`archive/`)
- Old development and diagnostic scripts (for reference only)
