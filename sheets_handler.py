import gspread
import pandas as pd
import config

def setup_client():
    """Sets up and authenticates the Google Sheets client."""
    try:
        client = gspread.service_account(filename='credentials.json')
        return client
    except Exception as e:
        print(f"An error occurred during Google Sheets authentication: {e}")
        return None

def setup_violation_details_sheet(client):
    """Ensures the 'Violation_Details' sheet exists with a header."""
    try:
        sheet = client.open(config.GOOGLE_SHEET_NAME)
        try:
            sheet.worksheet("Violation_Details")
        except gspread.exceptions.WorksheetNotFound:
            print("Creating new 'Violation_Details' sheet...")
            header = [['Main_Website', 'Sub_Page', 'Violation_ID', 'Severity', 'Description', 'Help_URL']]
            details_sheet = sheet.add_worksheet(title="Violation_Details", rows="1", cols=len(header[0]))
            details_sheet.append_rows(header)
    except Exception as e:
        print(f"Failed to setup violation details sheet: {e}")

def append_violation_details(client, details_rows):
    """Appends a list (batch) of violation rows to the 'Violation_Details' sheet."""
    if not details_rows:
        return
    try:
        sheet = client.open(config.GOOGLE_SHEET_NAME).worksheet("Violation_Details")
        # append_rows is designed for batching and is more efficient
        sheet.append_rows(details_rows, value_input_option='USER_ENTERED')
    except Exception as e:
        print(f"  !! CRITICAL: Failed to save violation details batch. Error: {e}")
        raise

def get_scored_pages_map(client):
    """
    Reads 'Accessibility_Scores' and returns a dictionary of {sub_page: main_website}
    for all pages that have been scored.
    """
    pages_map = {}
    try:
        sheet = client.open(config.GOOGLE_SHEET_NAME).worksheet("Accessibility_Scores")
        records = sheet.get_all_records()
        for record in records:
            sub_page = record.get('Sub_Page')
            main_site = record.get('Main_Website')
            if sub_page and main_site:
                pages_map[sub_page] = main_site
        return pages_map
    except Exception as e:
        print(f"Error reading 'Accessibility_Scores' sheet: {e}")
        return {}

def get_detailed_pages_set(client):
    """
    Reads 'Violation_Details' and returns a set of all Sub_Page URLs that
    already have their violation details logged.
    """
    pages_set = set()
    try:
        sheet = client.open(config.GOOGLE_SHEET_NAME).worksheet("Violation_Details")
        # Reading only the second column is efficient
        sub_page_column = sheet.col_values(2)
        pages_set.update(sub_page_column[1:])
        return pages_set
    except Exception as e:
        print(f"Warning: Could not read 'Violation_Details' sheet. Error: {e}")
        return set()