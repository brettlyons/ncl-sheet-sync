# NCL Sheet Sync

Automated tools for updating the SANS NCL Team Answer Sheet from cyberskyline.com data.

> **Note:** Built for a specific NCL team workflow. Documentation is functional but reflects organic development. Use as reference/inspiration rather than drop-in solution.

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

- Firefox logged into cyberskyline.com
- Google Sheets OAuth2 credentials
- NixOS (or Nix package manager)

## Setup

### Environment Setup

Use the provided shell.nix for a reproducible development environment:

```bash
cd ~/ncl-sheet-sync
nix-shell
```

This provides Python 3.12 with all required packages:
- gspread (Google Sheets API)
- google-auth-oauthlib (OAuth2 authentication)
- requests (HTTP client)
- sqlite (for cookie extraction)

Alternatively, you can run individual scripts directly with their nix-shell shebang (they have nix-shell directives in their headers).

### First-Time Setup

#### 1. Create Configuration File

```bash
cd ~/ncl-sheet-sync
cp config.example.py config.py
```

Edit `config.py` with your actual values:
- `SHEET_ID`: Your Google Sheet ID (from the URL)
- `CYBERSKYLINE_URL`: Your NCL Team Game world URL
- `COOKIE_FILE`: Path to your cyberskyline cookies file
- `TOKEN_PATH`: Path to your Google OAuth token file

#### 2. Google Sheets Authentication

**Option A: If you already have token.pickle**

If you've already authenticated (like the existing setup), just update the path in `config.py`:
```python
TOKEN_PATH = "~/token.pickle"
```

**Option B: First-time Google OAuth setup**

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
   - Download the credentials JSON file
5. Configure OAuth consent screen:
   - Add yourself as a test user
   - Scopes needed: Google Sheets API (read/write)
6. Run authentication script:
   ```bash
   cd ~/ncl-sheet-sync
   ./utils/setup_google_auth.py
   ```
   This will open a browser for OAuth authentication and create `token.pickle`.
7. Update `TOKEN_PATH` in `config.py` to point to your token.pickle

#### 3. Cyberskyline Cookie Extraction

Extract session cookies from Firefox while logged into cyberskyline.com:

```bash
# Find your Firefox profile
ls ~/.mozilla/firefox/*.default*/cookies.sqlite

# Extract cookies (replace with your profile path)
sqlite3 ~/.mozilla/firefox/YOUR_PROFILE.default/cookies.sqlite \
  "SELECT name, value FROM moz_cookies WHERE host LIKE '%cyberskyline.com%'" \
  | awk -F'|' '{printf "%s=%s; ", $1, $2}' > ~/cyberskyline_cookies.txt
```

Required cookies:
- `__stripe_mid`
- `__stripe_sid`
- `sky.sid`

Format in `cyberskyline_cookies.txt`:
```
__stripe_mid=...; __stripe_sid=...; sky.sid=...
```

Update `COOKIE_FILE` in `config.py` to point to this file.

#### 4. Get Your Sheet ID

From your Google Sheet URL:
```
https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit
```

Copy `YOUR_SHEET_ID_HERE` into `SHEET_ID` in `config.py`.

#### 5. Get Your Cyberskyline World URL

**Finding World IDs:**

1. Log into https://cyberskyline.com
2. Navigate to the world you want:
   - **Gymnasium**: Click "Training" → "NCL Gymnasium" or similar
   - **Team Game**: Click on your active team game when it's available
3. Look at the URL in your browser:
   ```
   https://cyberskyline.com/world/YOUR_WORLD_ID_HERE
   ```
4. Copy the full URL into `CYBERSKYLINE_URL` in `config.py`

**Example format:**
```python
# For testing with Gymnasium:
CYBERSKYLINE_URL = "https://cyberskyline.com/world/abc123gymnasium456"

# For actual competition (switch to this on Friday):
CYBERSKYLINE_URL = "https://cyberskyline.com/world/def789teamgame012"
```

**Note:** World IDs are unique to each competition/gym instance. The Gymnasium world ID stays the same, but Team Game world IDs change each season.

### Verifying Setup

Test your configuration:
```bash
cd ~/ncl-sheet-sync
./update_sheet.py osint  # Dry run to test authentication
```

If you see challenge data, authentication is working!

### Cookie Maintenance

Cyberskyline session cookies expire periodically. If you get authentication errors:

1. Make sure you're logged into cyberskyline.com in Firefox
2. Re-extract cookies using the sqlite3 command from step 3
3. Replace the contents of your cookies file

**Tip**: Session cookies typically last several hours to days. You may need to refresh them before each competition day.

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

When the NCL Team Game starts on Friday:

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
- `setup_google_auth.py` - Google OAuth authentication setup
- `extract_firefox_cookies.py` - Extract cyberskyline session cookies from Firefox

### Legacy Scripts (Optional)
- `update_all_sheets.py` - Alternative script to update all sheets
- `update_*_sheet.py` - Individual category updaters (9 files)

### Archive (`archive/`)
- Old development and diagnostic scripts (for reference only)
