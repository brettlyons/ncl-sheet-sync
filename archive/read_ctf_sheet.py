#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python312Packages.gspread python312Packages.google-auth-oauthlib

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def authenticate():
    """Authenticate with Google Sheets API using OAuth2"""
    creds = None
    token_path = '/home/blyons/token.pickle'

    # Check if we have a saved token
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # If there are no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '/home/blyons/Downloads/client_secret_37143557677-okjf3hibecjdflhejjtpsdr5akl64t19.apps.googleusercontent.com.json',
                SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return gspread.authorize(creds)

def read_sheet_structure(sheet_id):
    """Read and display the structure of the CTF tracking sheet"""
    gc = authenticate()

    # Open the spreadsheet
    spreadsheet = gc.open_by_key(sheet_id)

    print(f"Spreadsheet: {spreadsheet.title}")
    print(f"Number of sheets: {len(spreadsheet.worksheets())}\n")

    # List all worksheets (tabs)
    for worksheet in spreadsheet.worksheets():
        print(f"\n{'='*60}")
        print(f"Sheet: {worksheet.title}")
        print(f"Rows: {worksheet.row_count}, Columns: {worksheet.col_count}")

        # Get all values
        all_values = worksheet.get_all_values()

        if all_values:
            # Show header row
            print(f"\nHeader row: {all_values[0]}")

            # Show number of data rows
            data_rows = len(all_values) - 1
            print(f"Data rows: {data_rows}")

            # Show first few data rows as examples
            if data_rows > 0:
                print("\nFirst few rows:")
                for i, row in enumerate(all_values[1:6], 1):
                    print(f"  Row {i}: {row}")
        else:
            print("  (Empty sheet)")

    return spreadsheet

if __name__ == "__main__":
    # Extract sheet ID from the URL
    sheet_id = "1mguJ97pk7h4o-ogcaWrhxKnPPcZfXZcmEiyL5n22--k"
    read_sheet_structure(sheet_id)
