#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python312Packages.gspread python312Packages.google-auth-oauthlib python312Packages.requests

"""
Template for updating NCL category sheets
This file contains the core logic that can be used by individual sheet update scripts
"""

import gspread
from google.oauth2.credentials import Credentials
import os
import pickle
import requests
import re
import json
import sys

# Import configuration
try:
    from config import SHEET_ID, CYBERSKYLINE_URL, COOKIE_FILE, TOKEN_PATH
except ImportError:
    print("ERROR: config.py not found!")
    print("Please copy config.example.py to config.py and fill in your values.")
    sys.exit(1)

# Map cyberskyline category names to sheet tab names
CATEGORY_MAP = {
    "Open Source Intelligence": "OSINT",
    "Cryptography": "Crypto",
    "Password Cracking": "Cracking",
    "Log Analysis": "Log",
    "Network Traffic Analysis": "NTA",
    "Forensics": "Forensics",
    "Scanning & Reconnaissance": "Scanning",
    "Web Application Exploitation": "Web",
    "Enumeration & Exploitation": "Enum and Exploit"
}

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

def parse_category_challenges(preload_data, category_name):
    """Parse challenge data for a specific category"""
    modules = preload_data.get('report', {}).get('modules', [])

    for module in modules:
        if module['name'] == category_name:
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

def check_existing_work(worksheet, start_row, end_row):
    """
    Check if any work has been done in the sheet.
    Returns True if work found, False if safe to clear.
    """
    print(f"Safety check: Examining rows {start_row}-{end_row} for existing work...")

    # Read all cells in the range we'll be updating
    # Column D (Answer Status) and columns G-M (team members)
    try:
        # Get Answer Status column (D)
        answer_status_range = f'D{start_row}:D{end_row}'
        answer_status_cells = worksheet.get(answer_status_range)

        # Get team member columns (G-M)
        team_member_range = f'G{start_row}:M{end_row}'
        team_member_cells = worksheet.get(team_member_range)

        # Check Answer Status cells for non-default values
        for i, row in enumerate(answer_status_cells, start=start_row):
            if row and len(row) > 0:
                value = row[0].strip() if row[0] else ""
                # Non-default if it's not empty and not "N/A"
                if value and value != "N/A":
                    print(f"  ⚠ Found work in Answer Status (row {i}): '{value}'")
                    return True

        # Check team member cells for non-default values
        for i, row in enumerate(team_member_cells, start=start_row):
            if row:
                for col_idx, cell in enumerate(row):
                    value = cell.strip() if cell else ""
                    # Non-default if it's not empty and not "Nothing"
                    if value and value != "Nothing":
                        col_letter = chr(ord('G') + col_idx)  # G, H, I, J, K, L, M
                        print(f"  ⚠ Found work in team member column {col_letter} (row {i}): '{value}'")
                        return True

        print("  ✓ No existing work detected - safe to proceed")
        return False

    except Exception as e:
        print(f"  ⚠ Error checking for existing work: {e}")
        print("  Aborting update as a safety precaution")
        return True

def update_category_sheet(gc, sheet_name, challenge_clusters, test_mode=False):
    """Update a category sheet with challenge data"""
    spreadsheet = gc.open_by_key(SHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        print(f"ERROR: Sheet '{sheet_name}' not found")
        return False

    print(f"\n{'='*70}")
    print(f"Updating {sheet_name} Sheet")
    print(f"{'='*70}\n")

    # Start from row 50 for testing (will use row 3 in production)
    start_row = 50 if test_mode else 3
    end_row = 150 if test_mode else 100

    # Safety check: abort if any work has been done
    if check_existing_work(worksheet, start_row, end_row):
        print(f"\n{'='*70}")
        print("ERROR: Existing work detected in sheet!")
        print("Aborting update to prevent data loss.")
        print("Clear the sheet manually first if you want to regenerate it.")
        print(f"{'='*70}\n")
        return False

    # Clear existing data in the range
    print(f"Clearing rows {start_row}-{end_row}...")
    worksheet.batch_clear([f'A{start_row}:N{end_row}'])

    # Show what we're about to do
    print("\nChallenge structure from cyberskyline:")
    for i, cluster in enumerate(challenge_clusters, 1):
        print(f"  Challenge {i}: {cluster['name']}")
        print(f"    Questions: {len(cluster['questions'])}")
        print(f"    Total Points: {cluster['total_points']}")
        print(f"    Point distribution: {[q['points'] for q in cluster['questions']]}")
    print()

    current_row = start_row

    if test_mode:
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

            # Update columns A, D, and N
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

    # Apply updates
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
    # Add conditional formatting rules for Answer Status (D) and team member columns (G-M)
    conditional_format_requests = []

    # Build ranges for all question rows
    for row_num in question_rows:
        # Answer Status (Column D) conditional formatting
        # Yes = white text on green background
        conditional_format_requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': worksheet.id,
                        'startRowIndex': row_num - 1,
                        'endRowIndex': row_num,
                        'startColumnIndex': 3,  # Column D
                        'endColumnIndex': 4
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'TEXT_EQ',
                            'values': [{'userEnteredValue': 'Yes'}]
                        },
                        'format': {
                            'backgroundColor': {'green': 1},
                            'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'bold': True},
                            'backgroundColorStyle': {'rgbColor': {'green': 1}}
                        }
                    }
                },
                'index': 0
            }
        })

        # No = white text on red background
        conditional_format_requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': worksheet.id,
                        'startRowIndex': row_num - 1,
                        'endRowIndex': row_num,
                        'startColumnIndex': 3,
                        'endColumnIndex': 4
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'TEXT_EQ',
                            'values': [{'userEnteredValue': 'No'}]
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

        # N/A = black text on grey background
        conditional_format_requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': worksheet.id,
                        'startRowIndex': row_num - 1,
                        'endRowIndex': row_num,
                        'startColumnIndex': 3,
                        'endColumnIndex': 4
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'TEXT_EQ',
                            'values': [{'userEnteredValue': 'N/A'}]
                        },
                        'format': {
                            'backgroundColor': {'red': 0.85, 'green': 0.85, 'blue': 0.85},
                            'textFormat': {'foregroundColor': {}},
                            'backgroundColorStyle': {'rgbColor': {'red': 0.85, 'green': 0.85, 'blue': 0.85}}
                        }
                    }
                },
                'index': 0
            }
        })

        # Needs Validation = black text on beige/yellowish background
        conditional_format_requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': worksheet.id,
                        'startRowIndex': row_num - 1,
                        'endRowIndex': row_num,
                        'startColumnIndex': 3,
                        'endColumnIndex': 4
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'TEXT_EQ',
                            'values': [{'userEnteredValue': 'Needs Validation'}]
                        },
                        'format': {
                            'backgroundColor': {'red': 1, 'green': 0.95, 'blue': 0.8},
                            'textFormat': {'foregroundColor': {}},
                            'backgroundColorStyle': {'rgbColor': {'red': 1, 'green': 0.95, 'blue': 0.8}}
                        }
                    }
                },
                'index': 0
            }
        })

        # Ready to submit = dark green text on light green background
        conditional_format_requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': worksheet.id,
                        'startRowIndex': row_num - 1,
                        'endRowIndex': row_num,
                        'startColumnIndex': 3,
                        'endColumnIndex': 4
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'TEXT_EQ',
                            'values': [{'userEnteredValue': 'Ready to submit'}]
                        },
                        'format': {
                            'backgroundColor': {'red': 0.85, 'green': 0.92, 'blue': 0.83},
                            'textFormat': {'foregroundColor': {'green': 0.5}, 'bold': True},
                            'backgroundColorStyle': {'rgbColor': {'red': 0.85, 'green': 0.92, 'blue': 0.83}}
                        }
                    }
                },
                'index': 0
            }
        })

        # Team member columns (G-M) conditional formatting
        # Nothing = White
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

        # Started = Light green
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

        # Agree = Green, bold
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

        # Disagree = Red background, white bold text
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

        # Surrender = Black background, white bold text
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

    print(f"\n✓ {sheet_name} sheet updated successfully!")
    print(f"  - {len(challenge_clusters)} challenges")
    print(f"  - {sum(len(c['questions']) for c in challenge_clusters)} questions")
    print(f"  - Dropdowns added to Answer Status and team member columns")
    print(f"  - Challenge markers formatted with grey background")
    print(f"  - Conditional formatting applied for dropdown colors")

    return True
