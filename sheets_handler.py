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

def get_website_urls(client):
    """Reads website URLs from the source Google Sheet."""
    try:
        sheet = client.open(config.GOOGLE_SHEET_NAME).worksheet(config.SOURCE_SHEET_NAME)
        all_values = sheet.col_values(config.WEBSITE_URL_COLUMN)
        urls = all_values[3:] if len(all_values) > 3 else []
        return [url for url in urls if url.strip()]
    except Exception as e:
        print(f"An error occurred while reading from the source Google Sheet: {e}")
        return []

def setup_target_sheet(client):
    """Ensures the target sheet exists and has a header row."""
    try:
        sheet = client.open(config.GOOGLE_SHEET_NAME)
        try:
            target_sheet = sheet.worksheet(config.TARGET_SHEET_NAME)
            print(f"Found existing results sheet: '{config.TARGET_SHEET_NAME}'.")
        except gspread.exceptions.WorksheetNotFound:
            print(f"Creating new results sheet: '{config.TARGET_SHEET_NAME}'...")
            header = [[
                'Main_Website', 'Sub_Page', 'Ind_Compliance_Lvl', 'Total_Violation',
                'A_Violation', 'AA_Violation', 'AAA_Violation', 'Severe_Violation',
                'Moderate_Violation', 'Mild_Violation', 'Unknown_Violation', 'Date_Time'
            ]]
            target_sheet = sheet.add_worksheet(title=config.TARGET_SHEET_NAME, rows="1", cols=len(header[0]))
            target_sheet.append_rows(header)
            print("Sheet created successfully.")
    except Exception as e:
        print(f"Failed to setup target sheet. Error: {e}")

def get_audited_pages_map(client):
    """
    Reads the target sheet and returns a dictionary mapping each main website
    to a set of its already audited subpage URLs.
    """
    audited_map = {}
    try:
        sheet = client.open(config.GOOGLE_SHEET_NAME).worksheet(config.TARGET_SHEET_NAME)
        records = sheet.get_all_records()
        for record in records:
            main_site = record.get('Main_Website')
            sub_page = record.get('Sub_Page')
            if main_site and sub_page:
                if main_site not in audited_map:
                    audited_map[main_site] = set()
                audited_map[main_site].add(sub_page)
        return audited_map
    except Exception as e:
        print(f"Could not read the target sheet to determine progress. Error: {e}")
        return {}

def append_row(client, row_data):
    """Appends a single row of data to the target sheet."""
    try:
        sheet = client.open(config.GOOGLE_SHEET_NAME).worksheet(config.TARGET_SHEET_NAME)
        sheet.append_row(row_data)
    except Exception as e:
        print(f"  !! Failed to save result to Google Sheet. Error: {e}")

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
    """Appends a list of violation rows to the 'Violation_Details' sheet."""
    if not details_rows:
        return
    try:
        sheet = client.open(config.GOOGLE_SHEET_NAME).worksheet("Violation_Details")
        sheet.append_rows(details_rows)
    except Exception as e:
        print(f"  !! Failed to save violation details. Error: {e}")