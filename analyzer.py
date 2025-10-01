import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from axe_selenium_python import Axe
import config

def get_internal_links(base_url, limit):
    """Crawls a given URL to find a limited number of unique internal links."""
    if not base_url.startswith(('http://', 'https://')):
        base_url = 'https://' + base_url
    try:
        response = requests.get(base_url, timeout=config.TIMEOUT_SECONDS, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Could not fetch {base_url}. Error: {e}")
        return []
    soup = BeautifulSoup(response.text, 'html.parser')
    internal_links = set()
    base_domain = urlparse(base_url).netloc
    for link in soup.find_all('a', href=True):
        href = link['href']
        absolute_url = urljoin(base_url, href)
        parsed_url = urlparse(absolute_url)
        if (parsed_url.netloc == base_domain and
            parsed_url.scheme in ['http', 'https'] and
            not any(absolute_url.endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.zip', '.mailto'])):
            clean_url = parsed_url._replace(fragment="").geturl()
            if clean_url != base_url and clean_url + '/' != base_url:
                internal_links.add(clean_url)
        if len(internal_links) >= limit:
            break
    return list(internal_links)

def analyze_page(driver, url):
    """Analyzes a single page URL for WCAG compliance using the Axe engine."""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        print(f"  Navigating to: {url}")
        driver.set_page_load_timeout(config.TIMEOUT_SECONDS)
        driver.get(url)
        time.sleep(5)
        axe = Axe(driver)
        axe.inject()
        results = axe.run()
        return results
    except Exception as e:
        print(f"    Failed to analyze page {url}. Error: {e}")
        return None

def process_analysis_results(results):
    """
    Processes Axe results to count violations, determine compliance level,
    and extract detailed information about each violation.
    """
    if not results or 'violations' not in results:
        return {'error': 'Analysis failed or produced no results.'}

    violations = results['violations']
    counts = {'A': 0, 'AA': 0, 'AAA': 0}
    severity = {'severe': 0, 'moderate': 0, 'mild': 0, 'unknown': 0}
    impact_map = {'critical': 'severe', 'serious': 'severe', 'moderate': 'moderate', 'minor': 'mild'}
    
    # --- NEW: List to hold detailed violation info ---
    violation_details = []

    for v in violations:
        # This part extracts details for the new sheet
        violation_details.append({
            "id": v.get('id'),
            "impact": v.get('impact'),
            "description": v.get('description'),
            "help_url": v.get('helpUrl')
        })

        # This part is for the existing summary count
        is_wcag = False
        tags = v.get('tags', [])
        if any(tag in ['wcag2a', 'wcag21a'] for tag in tags):
            counts['A'] += 1
            is_wcag = True
        if any(tag in ['wcag2aa', 'wcag21aa'] for tag in tags):
            counts['AA'] += 1
            is_wcag = True
        if any(tag in ['wcag2aaa', 'wcag21aaa'] for tag in tags):
            counts['AAA'] += 1
            is_wcag = True
        
        if is_wcag:
            impact = v.get('impact')
            severity_key = impact_map.get(impact, 'unknown')
            severity[severity_key] += 1
    
    counts['total'] = counts['A'] + counts['AA'] + counts['AAA']

    if counts['A'] > 0:
        highest_pass_level = 'Below A'
    elif counts['AA'] > 0:
        highest_pass_level = 'A'
    elif counts['AAA'] > 0:
        highest_pass_level = 'AA'
    else:
        highest_pass_level = 'AAA'

    return {
        'highest_pass_level': highest_pass_level,
        'violations': counts,
        'severity': severity,
        'details': violation_details  # Return the new detailed list
    }