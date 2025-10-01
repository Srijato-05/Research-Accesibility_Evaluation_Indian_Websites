import gspread
import pandas as pd
from gspread_dataframe import set_with_dataframe

def get_sheet_as_df(spreadsheet, sheet_name, skiprows=0):
    """
    Safely reads a worksheet into a pandas DataFrame, allowing for rows to be skipped.
    """
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        all_values = sheet.get_all_values()
        
        if len(all_values) <= skiprows + 1:
            print(f"Warning: Worksheet '{sheet_name}' has no data rows to read after skipping.")
            return pd.DataFrame()

        header = all_values[skiprows]
        data = all_values[skiprows + 1:]
        
        df = pd.DataFrame(data, columns=header)
        df.columns = df.columns.str.strip()
        # Clean up any empty columns that might have been created
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df = df.loc[:, df.columns != '']
        return df

    except gspread.exceptions.WorksheetNotFound:
        print(f"Error: Worksheet '{sheet_name}' not found.")
        return None
    except Exception as e:
        print(f"An error occurred while reading sheet '{sheet_name}': {e}")
        return None


def cleanup_google_sheets_data():
    """
    Connects to Google Sheets, processes accessibility data, and
    creates a summarized 'Data_Cleanup' sheet.
    """
    # --- AUTHENTICATION ---
    try:
        gc = gspread.service_account(filename='credentials.json')
        spreadsheet = gc.open("Master_Sheet_Main")
        print("Successfully connected to your Google Sheet.")
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        return

    # --- DATA LOADING ---
    scores_df = get_sheet_as_df(spreadsheet, "Accessibility_Scores", skiprows=0)
    registry_df = get_sheet_as_df(spreadsheet, "Master_Website_Registry", skiprows=2)

    if scores_df is None or registry_df is None or scores_df.empty or registry_df.empty:
        print("Aborting due to errors reading the worksheets or no data found.")
        return
        
    print("Successfully loaded data from 'Accessibility_Scores' and 'Master_Website_Registry'.")

    # --- DATA PROCESSING ---
    url_col_registry = 'Website_URL (Home/Main)'
    name_col_registry = 'Website_Name'
    
    if url_col_registry not in registry_df.columns or name_col_registry not in registry_df.columns:
        print(f"Error: Registry sheet must contain '{url_col_registry}' and '{name_col_registry}' columns.")
        print(f"Columns found in registry: {registry_df.columns.tolist()}")
        return

    registry_df_unique = registry_df.drop_duplicates(subset=[url_col_registry])
    url_to_name_map = pd.Series(
        registry_df_unique[name_col_registry].values,
        index=registry_df_unique[url_col_registry]
    ).to_dict()

    scores_df['Website_Name'] = scores_df['Main_Website'].map(url_to_name_map)
    scores_df.dropna(subset=['Website_Name', 'Ind_Compliance_Lvl'], inplace=True)
    
    violation_cols = ['Total_Violation', 'Severe_Violation', 'Moderate_Violation', 'Mild_Violation']
    for col in violation_cols:
        if col in scores_df.columns:
            scores_df[col] = pd.to_numeric(scores_df[col], errors='coerce').fillna(0).astype(int)
        else:
            print(f"Warning: Column '{col}' not found in 'Accessibility_Scores' sheet.")

    # Corrected compliance order from worst to best
    compliance_order = ['Below A', 'A', 'AA', 'AAA']
    scores_df['Ind_Compliance_Lvl'] = pd.Categorical(
        scores_df['Ind_Compliance_Lvl'],
        categories=compliance_order,
        ordered=True
    )

    # --- AGGREGATION (with Subpage Count) ---
    agg_functions = {
        'Ind_Compliance_Lvl': 'min',
        'Total_Violation': 'sum',
        'Severe_Violation': 'sum',
        'Moderate_Violation': 'sum',
        'Mild_Violation': 'sum',
        'Sub_Page': 'count' # Count the number of sub_pages for each group
    }
    cleanup_df = scores_df.groupby('Website_Name').agg(agg_functions).reset_index()

    # Rename all columns for the final report
    cleanup_df.rename(columns={
        'Website_Name': 'Website_Name',
        'Ind_Compliance_Lvl': 'Overall_Compliance',
        'Total_Violation': 'Total_Violations',
        'Severe_Violation': 'Total_Severe_Violations',
        'Moderate_Violation': 'Total_Moderate_Violations',
        'Mild_Violation': 'Total_Mild_Violations',
        'Sub_Page': 'Subpages_Analyzed' # Rename the new count column
    }, inplace=True)

    # --- SAVING TO GOOGLE SHEETS ---
    try:
        try:
            cleanup_sheet = spreadsheet.worksheet("Data_Cleanup")
            cleanup_sheet.clear()
            print("Cleared existing 'Data_Cleanup' sheet.")
        except gspread.exceptions.WorksheetNotFound:
            cleanup_sheet = spreadsheet.add_worksheet(title="Data_Cleanup", rows="100", cols="20")
            print("Created new 'Data_Cleanup' sheet.")

        # Reorder columns for better presentation
        final_columns_order = [
            'Website_Name', 'Overall_Compliance', 'Subpages_Analyzed', 'Total_Violations',
            'Total_Severe_Violations', 'Total_Moderate_Violations', 'Total_Mild_Violations'
        ]
        cleanup_df = cleanup_df[final_columns_order]
        
        set_with_dataframe(cleanup_sheet, cleanup_df)
        print("Successfully wrote the summary to the 'Data_Cleanup' sheet.")
        
        print("\nHere's a preview of the final summary:")
        print(cleanup_df.head())

    except Exception as e:
        print(f"An error occurred while saving the data: {e}")


# --- Run the cleanup process ---
if __name__ == "__main__":
    cleanup_google_sheets_data()