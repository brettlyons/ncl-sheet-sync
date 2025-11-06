"""
Configuration template for Captain's Sheet Helper

Copy this file to config.py and fill in your actual values.
DO NOT commit config.py to git - it contains sensitive information.
"""

# Google Sheets configuration
SHEET_ID = "your-google-sheet-id-here"

# Cyberskyline configuration
# Use the appropriate URL for your needs:
# - Gymnasium URL for testing (has real challenge data)
# - Team Game URL for actual competition
CYBERSKYLINE_URL = "https://cyberskyline.com/world/your-world-id-here"

# Example URLs (replace with your actual world IDs):
# Gymnasium: https://cyberskyline.com/world/YOUR_GYMNASIUM_WORLD_ID
# Team Game: https://cyberskyline.com/world/YOUR_TEAM_GAME_WORLD_ID

# Authentication paths
COOKIE_FILE = "/path/to/your/cyberskyline_cookies.txt"
TOKEN_PATH = "/path/to/your/token.pickle"
