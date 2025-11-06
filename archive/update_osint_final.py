#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python312Packages.gspread python312Packages.google-auth-oauthlib python312Packages.requests

import gspread
from google.oauth2.credentials import Credentials
import os
import pickle
import requests
import re
import json

# Configuration
SHEET_ID = "1mguJ97pk7h4o-ogcaWrhxKnPPcZfXZcmEiyL5n22--k"
CYBERSKYLINE_URL = "https://cyberskyline.com/world/684c235bdbe1ed8e2a7f7e72"
COOKIE_FILE = "/home/blyons/cyberskyline_cookies.txt"
TOKEN_PATH = "/home/blyons/token.pickle"

# Data validation rules
ANSWER_STATUS_VALIDATION = {
    'condition': {
        'type': 'ONE_OF_LIST',
        'values': [
            {'userEnteredValue': 'Yes'},
            {'userEnteredValue': 'No'},
            {'userEnteredValue': 'N/A'},
            {'userEnteredValue': 'Needs Validation'},
            {'userEnteredValue': 'Ready to submit'}
        ]
    },
    'strict': True,
    'showCustomUi': True
}

TEAM_MEMBER_VALIDATION = {
    'condition': {
        'type': 'ONE_OF_LIST',
        'values': [
            {'userEnteredValue': 'Nothing'},
            {'userEnteredValue': 'Started'},
            {'userEnteredValue': 'Agree'},
            {'userEnteredValue': 'Disagree'},
            {'userEnteredValue': 'Surrender'}
        ]
    },
    'strict': True,
    'showCustomUi': True
}

def authenticate_gsheets():
    """Authenticate with Google Sheets API"""
    with open(TOKEN_PATH, 'rb') as token:
        creds = pickle.load(token)
    return gspread.authorize(creds)

def fetch_cyberskyline_data():
    """Fetch challenge data from cyberskyline"""
    with open(COOKIE_FILE, 'r') as f:
        cookies_str = f.read().strip()

    headers = {
        'Cookie': cookies_str,
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0'
    }

    response = requests.get(CYBERSKYLINE_URL, headers=headers)
    match = re.search(r'window\.preload\s*=\s*({.*?});', response.text, re.DOTALL)
    preload_data = json.loads(match.group(1))
    return preload_data

def parse_osint_challenges(preload_data):
    """Parse OSINT challenge data"""
    modules = preload_data.get('report', {}).get('modules', [])

    for module in modules:
        if module['name'] == "Open Source Intelligence":
            challenge_clusters = []

            for cluster in module.get('clusters', []):
                cluster_name = cluster['name']
                num_questions = cluster['challenges']
                cluster_points = cluster['points']

                questions = []
                if num_questions > 0:
                    avg_points = cluster_points // num_questions

                    for i in range(num_questions):
                        if i == num_questions - 1:
                            points = cluster_points - (avg_points * (num_questions - 1))
                        else:
                            points = avg_points

                        questions.append({
                            'points': points,
                            'index': i + 1
                        })

                challenge_clusters.append({
                    'name': cluster_name,
                    'questions': questions,
                    'total_points': cluster_points
                })

            return challenge_clusters

    return []

def update_osint_sheet(gc, challenge_clusters):
    """Update the OSINT sheet, creating proper structure"""
    spreadsheet = gc.open_by_key(SHEET_ID)
    worksheet = spreadsheet.worksheet("OSINT")

    print(f"\n{'='*70}")
    print(f"Updating OSINT Sheet")
    print(f"{'='*70}\n")

    # Show what we're about to do
    print("Challenge structure from cyberskyline:")
    for i, cluster in enumerate(challenge_clusters, 1):
        print(f"  Challenge {i}: {cluster['name']}")
        print(f"    Questions: {len(cluster['questions'])}")
        print(f"    Total Points: {cluster['total_points']}")
        print(f"    Point distribution: {[q['points'] for q in cluster['questions']]}")
        print()

    # Start from row 50 for testing (will use row 3 in production)
    import sys
    start_row = 50 if '--test' in sys.argv else 3
    current_row = start_row

    if '--test' in sys.argv:
        print("*** TEST MODE: Writing to rows 50+ to avoid clobbering data ***\n")

    updates = []

    # Track question rows for adding validation later
    question_rows = []
    marker_rows = []

    for cluster in challenge_clusters:
        # Add challenge marker row
        print(f"Row {current_row}: Challenge marker '{cluster['name']}'")
        marker_rows.append(current_row)
        updates.append({
            'range': f'A{current_row}',
            'values': [[cluster['name']]]
        })

        current_row += 1

        # Add question rows
        for question in cluster['questions']:
            question_text = f"Question {question['index']}"
            print(f"  Row {current_row}: {question_text} - {question['points']} points")

            question_rows.append(current_row)

            # Update columns A and N
            updates.append({
                'range': f'A{current_row}',
                'values': [[question_text]]
            })
            updates.append({
                'range': f'D{current_row}',
                'values': [['N/A']]  # Default Answer Status
            })
            updates.append({
                'range': f'N{current_row}',
                'values': [[question['points']]]
            })

            # Set default values for team member columns (columns G-M)
            updates.append({
                'range': f'G{current_row}:M{current_row}',
                'values': [['Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing']]
            })

            current_row += 1

        # Add blank row after each challenge
        current_row += 1

    print(f"\n{'='*70}")
    print(f"Total rows to update: {current_row - start_row}")
    print(f"Starting at row: {start_row}")
    print(f"Ending at row: {current_row - 1}")
    print(f"{'='*70}\n")

    # Check for --yes flag
    import sys
    if '--yes' in sys.argv:
        print("Updating cell values...")
        worksheet.batch_update(updates)

        print("Adding data validation (dropdowns)...")
        # Build validation requests for all question rows
        validation_requests = []

        for row_num in question_rows:
            row_index = row_num - 1  # 0-indexed

            # Column D (Answer Status) validation
            validation_requests.append({
                'setDataValidation': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': row_index,
                        'endRowIndex': row_index + 1,
                        'startColumnIndex': 3,  # Column D
                        'endColumnIndex': 4
                    },
                    'rule': ANSWER_STATUS_VALIDATION
                }
            })

            # Columns G-M (Team member) validation
            for col_idx in range(6, 13):  # Columns G-M (0-indexed: 6-12)
                validation_requests.append({
                    'setDataValidation': {
                        'range': {
                            'sheetId': worksheet.id,
                            'startRowIndex': row_index,
                            'endRowIndex': row_index + 1,
                            'startColumnIndex': col_idx,
                            'endColumnIndex': col_idx + 1
                        },
                        'rule': TEAM_MEMBER_VALIDATION
                    }
                })

        # Apply validations in batch
        spreadsheet.batch_update({'requests': validation_requests})

        print("Applying cell formatting (colors, borders)...")
        # Format all cells
        format_requests = []

        # Grey background for marker rows
        for row_num in marker_rows:
            format_requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': row_num - 1,  # 0-indexed
                        'endRowIndex': row_num,
                        'startColumnIndex': 0,
                        'endColumnIndex': 14  # Columns A-N
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.85,
                                'green': 0.85,
                                'blue': 0.85
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.backgroundColor'
                }
            })

        # Format question rows
        for row_num in question_rows:
            row_index = row_num - 1

            # White background for all cells in question rows
            format_requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': row_index,
                        'endRowIndex': row_index + 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': 14
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 1, 'green': 1, 'blue': 1},
                            'borders': {
                                'top': {'style': 'SOLID', 'width': 1},
                                'bottom': {'style': 'SOLID', 'width': 1},
                                'left': {'style': 'SOLID', 'width': 1},
                                'right': {'style': 'SOLID', 'width': 1}
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.backgroundColor,userEnteredFormat.borders'
                }
            })

            # White text for team member columns G-M (makes "Nothing" invisible)
            format_requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': row_index,
                        'endRowIndex': row_index + 1,
                        'startColumnIndex': 6,  # Column G
                        'endColumnIndex': 13  # Column M
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {
                                'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.textFormat.foregroundColor'
                }
            })

        spreadsheet.batch_update({'requests': format_requests})

        print("Adding conditional formatting for dropdown colors...")
        # Add conditional formatting rules for team member columns (G-M)
        conditional_format_requests = []

        # Build ranges for all question rows (columns G-M)
        for row_num in question_rows:
            conditional_format_requests.append({
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{
                            'sheetId': worksheet.id,
                            'startRowIndex': row_num - 1,
                            'endRowIndex': row_num,
                            'startColumnIndex': 6,  # Column G
                            'endColumnIndex': 13  # Column M
                        }],
                        'booleanRule': {
                            'condition': {
                                'type': 'TEXT_EQ',
                                'values': [{'userEnteredValue': 'Nothing'}]
                            },
                            'format': {
                                'backgroundColor': {'red': 1, 'green': 1, 'blue': 1},
                                'textFormat': {'foregroundColor': {}},
                                'backgroundColorStyle': {'rgbColor': {'red': 1, 'green': 1, 'blue': 1}}
                            }
                        }
                    },
                    'index': 0
                }
            })

            conditional_format_requests.append({
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{
                            'sheetId': worksheet.id,
                            'startRowIndex': row_num - 1,
                            'endRowIndex': row_num,
                            'startColumnIndex': 6,
                            'endColumnIndex': 13
                        }],
                        'booleanRule': {
                            'condition': {
                                'type': 'TEXT_EQ',
                                'values': [{'userEnteredValue': 'Started'}]
                            },
                            'format': {
                                'backgroundColor': {'red': 0.8509804, 'green': 0.91764706, 'blue': 0.827451},
                                'textFormat': {'foregroundColor': {}},
                                'backgroundColorStyle': {'rgbColor': {'red': 0.8509804, 'green': 0.91764706, 'blue': 0.827451}}
                            }
                        }
                    },
                    'index': 0
                }
            })

            conditional_format_requests.append({
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{
                            'sheetId': worksheet.id,
                            'startRowIndex': row_num - 1,
                            'endRowIndex': row_num,
                            'startColumnIndex': 6,
                            'endColumnIndex': 13
                        }],
                        'booleanRule': {
                            'condition': {
                                'type': 'TEXT_EQ',
                                'values': [{'userEnteredValue': 'Agree'}]
                            },
                            'format': {
                                'backgroundColor': {'green': 1},
                                'textFormat': {'foregroundColor': {}, 'bold': True},
                                'backgroundColorStyle': {'rgbColor': {'green': 1}}
                            }
                        }
                    },
                    'index': 0
                }
            })

            conditional_format_requests.append({
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{
                            'sheetId': worksheet.id,
                            'startRowIndex': row_num - 1,
                            'endRowIndex': row_num,
                            'startColumnIndex': 6,
                            'endColumnIndex': 13
                        }],
                        'booleanRule': {
                            'condition': {
                                'type': 'TEXT_EQ',
                                'values': [{'userEnteredValue': 'Disagree'}]
                            },
                            'format': {
                                'backgroundColor': {'red': 1},
                                'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'bold': True},
                                'backgroundColorStyle': {'rgbColor': {'red': 1}}
                            }
                        }
                    },
                    'index': 0
                }
            })

            conditional_format_requests.append({
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{
                            'sheetId': worksheet.id,
                            'startRowIndex': row_num - 1,
                            'endRowIndex': row_num,
                            'startColumnIndex': 6,
                            'endColumnIndex': 13
                        }],
                        'booleanRule': {
                            'condition': {
                                'type': 'TEXT_EQ',
                                'values': [{'userEnteredValue': 'Surrender'}]
                            },
                            'format': {
                                'backgroundColor': {},
                                'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'bold': True},
                                'backgroundColorStyle': {'rgbColor': {}}
                            }
                        }
                    },
                    'index': 0
                }
            })

        # Apply conditional formatting in batches (max 100 requests at a time)
        batch_size = 100
        for i in range(0, len(conditional_format_requests), batch_size):
            batch = conditional_format_requests[i:i+batch_size]
            spreadsheet.batch_update({'requests': batch})

        print("\n✓ OSINT sheet updated successfully!")
        print(f"  - {len(challenge_clusters)} challenges")
        print(f"  - {sum(len(c['questions']) for c in challenge_clusters)} questions")
        print(f"  - Dropdowns added to Answer Status and team member columns")
        print(f"  - Challenge markers formatted with grey background")
    else:
        print("\nUse --yes flag to actually update the sheet")
        print("Preview only - no changes made.")

def main():
    print("Fetching data from cyberskyline...")
    preload_data = fetch_cyberskyline_data()

    print("Parsing OSINT challenges...")
    challenges = parse_osint_challenges(preload_data)

    print(f"Found {len(challenges)} challenges with {sum(len(c['questions']) for c in challenges)} total questions\n")

    print("Authenticating with Google Sheets...")
    gc = authenticate_gsheets()

    update_osint_sheet(gc, challenges)

    return 0

if __name__ == "__main__":
    exit(main())
