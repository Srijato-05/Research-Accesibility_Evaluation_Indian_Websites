import gspread
import pandas as pd
from gspread_dataframe import set_with_dataframe
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def setup_driver():
    """Initializes a headless Chrome WebDriver."""
    print("Setting up headless browser...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_gspread
import pandas as pd
from gspread_dataframe import set_with_dataframe
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
from urllib.parse import quote_plus

def setup_driver():
    """Initializes a headless Chrome WebDriver."""
    print("Setting up headless browser...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
    options.add_argument('--log-level=3')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        driver.set_page_load_timeout(30) # Increased timeout for slow sites
        return driver
    except Exception as e:
        print(f"Could not start browser: {e}")
        return None

def get_context_from_website_content(driver, url):
    """
    Visits a URL and extracts text from key HTML tags (title, meta description,
    headings, and paragraphs) to build a rich context for classification.
    """
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        print(f"  -> Analyzing content from {url}...")
        driver.get(url)
        time.sleep(3) # Allow more time for JS-heavy pages to render
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        context_parts = []
        
        # 1. Get title and meta description (high value)
        title = soup.title.string if soup.title else ''
        context_parts.append(title.lower())
        
        description_tag = soup.find('meta', attrs={'name': 'description'})
        description = description_tag['content'] if description_tag else ''
        context_parts.append(description.lower())
        
        # 2. Get text from the first few important tags for relevance
        headings = soup.find_all(['h1', 'h2'], limit=5)
        paragraphs = soup.find_all('p', limit=10)
        
        for h in headings:
            context_parts.append(h.get_text().lower())
        for p in paragraphs:
            context_parts.append(p.get_text().lower())
            
        full_context = ' '.join(context_parts)
        # Clean up excessive whitespace for better matching
        full_context = ' '.join(full_context.split())

        if not full_context or len(full_context) < 50: # Check for minimal content
            print(f"  -> Could not extract meaningful text from the page.")
            return ""
        return full_context
    except Exception as e:
        print(f"  - Could not analyze page content. Error: {e}")
        return ""

def get_sheet_as_df(spreadsheet, sheet_name, skiprows=0):
    """Safely reads a worksheet into a pandas DataFrame."""
    try:
        sheet = spreadsheet.worksheet(sheet_name)
        all_values = sheet.get_all_values()
        if len(all_values) <= skiprows: return pd.DataFrame()
        header, data = all_values[skiprows], all_values[skiprows + 1:]
        df = pd.DataFrame(data, columns=header)
        df.columns = df.columns.str.strip()
        return df.loc[:, ~df.columns.str.contains('^Unnamed')].loc[:, df.columns != '']
    except Exception as e:
        print(f"Error reading sheet '{sheet_name}': {e}"); return None

def automate_subsector_classification():
    """
    Classifies websites by analyzing their homepage content and updates a
    dedicated column in the Google Sheet.
    """
    print("Starting content-based sub-sector automation...")
    try:
        gc = gspread.service_account(filename='credentials.json')
        spreadsheet = gc.open("Master_Sheet_Main")
        registry_sheet = spreadsheet.worksheet("Master_Website_Registry")
        print("Successfully connected to your Google Sheet.")
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}"); return

    registry_df = get_sheet_as_df(spreadsheet, "Master_Website_Registry", skiprows=2)
    if registry_df is None or registry_df.empty:
        print("Could not load 'Master_Website_Registry'. Aborting."); return
    
    # --- EXPANDED & REFINED KEYWORD DICTIONARY ---
    subsector_map = {
        'Government / Public Service': ['government of india', 'ministry of', 'department of', 'public service', 'governance'],
        'IT Services & Consulting': ['it services', 'consulting', 'digital transformation', 'tcs', 'infosys', 'wipro'],
        'Private Sector Bank': ['private sector bank', 'personal banking', 'corporate banking'],
        'Public Sector Bank': ['public sector bank', 'sarkari bank', 'government undertaking', 'sbi', 'pnb'],
        'Stock Broker / Investment': ['stock broker', 'trading platform', 'demat account', 'investing', 'mutual funds', 'zerodha'],
        'FinTech / Payments': ['online payments', 'payment gateway', 'upi', 'wallet', 'paytm', 'phonepe'],
        'Insurance': ['insurance', 'life cover', 'health insurance', 'car insurance', 'policybazaar', 'lic'],
        'E-commerce Marketplace': ['online shopping', 'e-commerce', 'marketplace', 'buy online', 'amazon', 'flipkart'],
        'Fashion & Apparel': ['fashion', 'clothing', 'apparel', 'lifestyle store', 'footwear', 'myntra'],
        'Online Grocery': ['online grocery', 'grocery delivery', 'fresh vegetables', 'bigbasket', 'blinkit'],
        'News Media': ['news', 'latest news', 'breaking news', 'media house', 'newspaper'],
        'OTT Platform': ['streaming service', 'watch movies', 'tv shows', 'web series', 'hotstar', 'jiocinema'],
        'Hospital / Healthcare': ['hospital', 'healthcare services', 'multi-speciality', 'apollo', 'fortis'],
        'Online Pharmacy / HealthTech': ['online pharmacy', 'buy medicines', 'health products', 'practo', '1mg'],
        'Diagnostic Lab': ['diagnostic', 'pathology', 'lab tests', 'health checkup'],
        'University / College': ['university', 'college', 'institute of technology', 'iit', 'iim', 'education'],
        'EdTech': ['online learning', 'edtech platform', 'online courses', 'e-learning', "byju's", 'unacademy'],
        'Automotive Manufacturer': ['automotive', 'car manufacturer', 'motorcycles', 'vehicles', 'tata motors'],
        'Food Delivery': ['food delivery', 'order food online', 'zomato', 'swiggy'],
        'Real Estate Portal': ['real estate', 'property portal', 'buy rent sell', 'apartments', 'magicbricks'],
        'Airline / Aviation': ['airline', 'flight tickets', 'book flights', 'indigo', 'air india'],
        'Telecom Provider': ['telecom', 'mobile network', 'broadband', 'jio', 'airtel', 'vi'],
    }

    driver = setup_driver()
    if not driver: return
    
    new_column_name = 'Automated_Sub_Sector'
    if new_column_name not in registry_df.columns:
        registry_df[new_column_name] = ''

    rows_to_classify = registry_df[registry_df[new_column_name].str.strip() == ''].index
    print(f"Found {len(rows_to_classify)} websites to classify.")

    for index in rows_to_classify:
        row = registry_df.loc[index]
        url = row['Website_URL (Home/Main)']
        name = row['Website_Name']
        print(f"\nAnalyzing: {name}")
        
        context = get_context_from_website_content(driver, url)
        if context:
            classified = False
            for sub_sector, keywords in subsector_map.items():
                if any(keyword in context for keyword in keywords):
                    registry_df.at[index, new_column_name] = sub_sector
                    print(f"  -> Classified as: {sub_sector}")
                    classified = True
                    break
            if not classified:
                print("  -> No specific sub-sector matched.")
    
    driver.quit()
    print(f"\nFinished analysis.")

    # --- SAFELY UPDATE ONLY THE NEW COLUMN ---
    try:
        print("Updating Google Sheet with new classifications...")
        header_list = registry_sheet.row_values(3)
        if new_column_name not in header_list:
            registry_sheet.update_cell(3, len(header_list) + 1, new_column_name)
            header_list.append(new_column_name)

        col_index = header_list.index(new_column_name) + 1
        col_letter = gspread.utils.rowcol_to_a1(1, col_index).rstrip('1')
        
        values_to_update = registry_df[[new_column_name]].values.tolist()
        update_range = f'{col_letter}4:{col_letter}{len(registry_df) + 3}'

        registry_sheet.update(update_range, values_to_update)
        print("Successfully updated the 'Automated_Sub_Sector' column in your sheet.")

    except Exception as e:
        print(f"An error occurred while saving the data: {e}")

if __name__ == "__main__":
    automate_subsector_classification()