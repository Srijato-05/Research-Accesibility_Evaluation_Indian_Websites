import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import config
import sheets_handler
import analyzer

def setup_driver():
    """Initializes and returns a headless Chrome WebDriver."""
    print("Setting up local Chrome browser for testing...")
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
        print(f"Could not start the local Chrome browser. Error: {e}")
        return None

def main():
    """Main function to orchestrate the accessibility audit."""
    print("Starting WCAG Accessibility Auditor...")
    g_client = sheets_handler.setup_client()
    if not g_client: return

    # --- SETUP AND RESUME LOGIC ---
    sheets_handler.setup_target_sheet(g_client)
    urls_to_audit = sheets_handler.get_website_urls(g_client)
    if not urls_to_audit:
        print("No website URLs found in the source sheet. Exiting.")
        return

    # Get a map of all previously audited pages for all websites
    audited_pages_map = sheets_handler.get_audited_pages_map(g_client)
    print(f"Found {len(urls_to_audit)} total websites to check. Will audit up to {config.TARGET_SUBPAGE_COUNT} pages per site.")

    driver = setup_driver()
    if not driver: return

    for base_url in urls_to_audit:
        # --- DYNAMIC AUDIT LOGIC ---
        audited_subpages = audited_pages_map.get(base_url, set())
        audited_count = len(audited_subpages)

        if audited_count >= config.TARGET_SUBPAGE_COUNT:
            print(f"\n--- Skipping '{base_url}'. Already has {audited_count} pages (target is {config.TARGET_SUBPAGE_COUNT}). ---")
            continue

        print(f"\n--- Auditing '{base_url}'. Found {audited_count} existing pages. ---")
        
        needed_count = config.TARGET_SUBPAGE_COUNT - audited_count
        pages_to_check = []
        
        # 1. Check if the base URL (homepage) itself has been audited
        if base_url not in audited_subpages:
            pages_to_check.append(base_url)
        
        # 2. Find new, unique internal links to top up the list
        # We fetch more than needed to account for duplicates and already audited links
        print(f"  Searching for {needed_count} new subpages to meet the target...")
        found_links = analyzer.get_internal_links(base_url, limit=config.TARGET_SUBPAGE_COUNT * 2)
        
        new_links_found = 0
        for link in found_links:
            if link not in audited_subpages:
                pages_to_check.append(link)
                new_links_found += 1
                if new_links_found >= needed_count:
                    break
        
        if not pages_to_check:
            print("  No new, un-audited subpages were found.")
            continue
        
        print(f"  Proceeding to audit {len(pages_to_check)} new page(s).")
        # --- END OF DYNAMIC LOGIC ---

        for page_url in pages_to_check:
            analysis_results = analyzer.analyze_page(driver, page_url)
            if analysis_results:
                processed_data = analyzer.process_analysis_results(analysis_results)
                if 'error' in processed_data:
                    print(f"    Could not process results: {processed_data['error']}")
                    continue

                v = processed_data['violations']
                s = processed_data['severity']
                print(f"    Compliance: {processed_data['highest_pass_level']} | Total WCAG Violations: {v['total']} "
                      f"(A: {v['A']}, AA: {v['AA']}, AAA: {v['AAA']})")
                print(f"    Severity: Severe: {s['severe']}, Moderate: {s['moderate']}, Mild: {s['mild']}")

                row_data = [
                    base_url, page_url, processed_data['highest_pass_level'], v['total'],
                    v['A'], v['AA'], v['AAA'], s['severe'],
                    s['moderate'], s['mild'], s['unknown'],
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
                sheets_handler.append_row(g_client, row_data)
            else:
                print(f"    Skipping analysis for {page_url} due to error.")

    driver.quit()
    print("\nAudit complete.")

if __name__ == "__main__":
    main()