import concurrent.futures
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import config
import sheets_handler
import analyzer

def create_driver():
    """Initializes a single headless Chrome WebDriver instance."""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
    options.add_argument('--log-level=3')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--disable-blink-features=AutomationControlled')
    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        return driver
    except Exception as e:
        # This error will be caught by the worker and logged.
        return None

def worker_task(page_url, base_url):
    """
    The task for a single worker thread. It creates its own driver, analyzes
    a page with retries, and returns the results.
    """
    driver = create_driver()
    if not driver:
        return page_url, None # Return failure if driver fails

    for attempt in range(config.RETRY_ATTEMPTS):
        analysis_results = analyzer.analyze_page(driver, page_url)
        if analysis_results:
            processed_data = analyzer.process_analysis_results(analysis_results)
            if 'error' not in processed_data:
                details_to_log = []
                for detail in processed_data.get('details', []):
                    details_to_log.append([
                        base_url, page_url, detail.get('id'), detail.get('impact'),
                        detail.get('description'), detail.get('help_url')
                    ])
                driver.quit()
                return page_url, details_to_log
        # If analysis fails, wait a moment before retrying
        time.sleep(2)

    driver.quit()
    return page_url, None # Return None on persistent failure

def main():
    """
    Uses a parallel processing pool to efficiently backfill the
    Violation_Details sheet.
    """
    print("Starting Advanced Violation Details generation script...")
    g_client = sheets_handler.setup_client()
    if not g_client: return

    sheets_handler.setup_violation_details_sheet(g_client)
    
    pages_to_process = sheets_handler.get_scored_pages_map(g_client)
    if not pages_to_process:
        print("No pages found in 'Accessibility_Scores' to process. Exiting."); return

    detailed_pages = sheets_handler.get_detailed_pages_set(g_client)
    print(f"Found {len(pages_to_process)} pages in Accessibility_Scores.")
    print(f"Found {len(detailed_pages)} pages already logged in Violation_Details.")

    pages_to_analyze = {url: main_site for url, main_site in pages_to_process.items() if url not in detailed_pages}

    if not pages_to_analyze:
        print("All pages are already up to date. No new details to generate. Exiting.")
        return
        
    print(f"Proceeding to analyze {len(pages_to_analyze)} missing pages using {config.NUM_WORKERS} parallel workers.")
    
    results_batch = []
    failed_pages = []

    # Using ThreadPoolExecutor for I/O-bound tasks like web browsing
    with concurrent.futures.ThreadPoolExecutor(max_workers=config.NUM_WORKERS) as executor:
        # Prepare future tasks
        future_to_url = {executor.submit(worker_task, url, base): url for url, base in pages_to_analyze.items()}
        
        # Process results as they complete, with a progress bar
        for future in tqdm(concurrent.futures.as_completed(future_to_url), total=len(pages_to_analyze), desc="Analyzing Pages"):
            page_url = future_to_url[future]
            try:
                original_url, violation_details = future.result()
                if violation_details is not None:
                    results_batch.extend(violation_details)
                else:
                    failed_pages.append(original_url)

                # When the batch is full, write it to the sheet
                if len(results_batch) >= config.BATCH_SIZE:
                    print(f"\nWriting a batch of {len(results_batch)} violation details to Google Sheets...")
                    sheets_handler.append_violation_details(g_client, results_batch)
                    results_batch = [] # Reset the batch

            except Exception as exc:
                failed_pages.append(page_url)
                print(f"\n{page_url} generated an exception: {exc}")

    # Write any remaining results in the last batch
    if results_batch:
        print(f"\nWriting the final batch of {len(results_batch)} violation details...")
        sheets_handler.append_violation_details(g_client, results_batch)

    print("\nViolation details generation complete.")
    if failed_pages:
        print("\nThe following pages failed to analyze after multiple attempts and should be reviewed manually:")
        for url in failed_pages:
            print(f"- {url}")

if __name__ == "__main__":
    main()