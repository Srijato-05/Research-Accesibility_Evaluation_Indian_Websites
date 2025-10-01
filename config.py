# --- CONFIGURATION ---
# --- Please update these values ---

# Google Sheet Details
GOOGLE_SHEET_NAME = "Master_Sheet_Main"
SOURCE_SHEET_NAME = "Master_Website_Registry"
TARGET_SHEET_NAME = "Accessibility_Scores"
WEBSITE_URL_COLUMN = 2
CREDENTIALS_FILE = "credentials.json"

# --- NEW: Dynamic Crawler Details ---
# The script will try to ensure each website has at least this many subpages audited.
# If a site has fewer than this number, the script will crawl for more pages to meet the target.
TARGET_SUBPAGE_COUNT = 10
# How many seconds to wait for a page to load before timing out.
TIMEOUT_SECONDS = 30