# --- CONFIGURATION ---
# --- Please update these values ---

# Google Sheet Details
GOOGLE_SHEET_NAME = "Master_Sheet_Main"
SOURCE_SHEET_NAME = "Master_Website_Registry"
TARGET_SHEET_NAME = "Accessibility_Scores"
WEBSITE_URL_COLUMN = 2
CREDENTIALS_FILE = "credentials.json"

# --- Main Audit Script Settings ---
TARGET_SUBPAGE_COUNT = 10
TIMEOUT_SECONDS = 30

# --- NEW: Advanced Violation Details Script Settings ---

# Number of parallel browser instances to run.
# A good starting point is the number of CPU cores you have.
# Be cautious: a high number will use more memory and CPU.
NUM_WORKERS = 4

# Number of page results to collect before writing to Google Sheets in a single batch.
# A larger batch is more efficient but uses more memory.
BATCH_SIZE = 20

# Number of times to retry analyzing a page if it fails.
RETRY_ATTEMPTS = 2