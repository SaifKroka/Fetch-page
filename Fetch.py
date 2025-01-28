import argparse
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import os
from colorama import Fore, Style, init

# Initialize colorama for colorful terminal output
init(autoreset=True)

def fetch_page_source(url, headers=None):
    """Fetch the HTML source code of a given URL."""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}[-] Error fetching URL {url}: {e}{Style.RESET_ALL}")
        return None

def fetch_js_files(html_content, base_url):
    """Extract and fetch content from JavaScript files in the HTML."""
    soup = BeautifulSoup(html_content, "html.parser")
    js_files = [
        urljoin(base_url, script.get("src"))
        for script in soup.find_all("script", src=True)
    ]

    js_content = ""
    for js_file in js_files:
        print(f"{Fore.YELLOW}[!] Fetching JavaScript file: {js_file}{Style.RESET_ALL}")
        js_data = fetch_page_source(js_file)
        if js_data:
            js_content += js_data + "\n"

    return js_content

def extract_endpoints_from_source(html_content, base_url):
    """Extract all potential API endpoints from HTML and JavaScript content."""
    endpoints = set()

    # Regex for URLs and API patterns
    url_regex = re.compile(
        r"https?://[^\s\"'<>\(\)]+|/[\w\-./?=&]+"
    )

    # Extract all matches for URLs
    for match in url_regex.findall(html_content):
        full_url = urljoin(base_url, match) if match.startswith('/') else match
        parsed_url = urlparse(full_url)
        # Filter for endpoints with a path (indicating an API or resource)
        if parsed_url.netloc and parsed_url.path:
            endpoints.add(full_url)

    return list(endpoints)

def scrape_page_and_find_endpoints(url, visited_urls, depth=1, headers=None):
    """Scrape the page, find endpoints, and optionally navigate linked pages."""
    if depth <= 0 or url in visited_urls:
        return []

    visited_urls.add(url)
    print(f"{Fore.BLUE}[+] Scraping: {url}{Style.RESET_ALL}")
    html_content = fetch_page_source(url, headers=headers)

    if not html_content:
        return []

    # Extract endpoints from the current page
    endpoints = extract_endpoints_from_source(html_content, base_url=url)

    # Fetch and analyze JavaScript files
    js_content = fetch_js_files(html_content, url)
    if js_content:
        js_endpoints = extract_endpoints_from_source(js_content, base_url=url)
        endpoints.extend(js_endpoints)

    # Extract links to navigate further
    soup = BeautifulSoup(html_content, "html.parser")
    links = [
        urljoin(url, link.get("href")) 
        for link in soup.find_all("a", href=True)
    ]

    # Filter for unique internal links
    internal_links = set(link for link in links if urlparse(link).netloc == urlparse(url).netloc)

    # Recursively scrape linked pages
    for link in internal_links:
        endpoints.extend(scrape_page_and_find_endpoints(link, visited_urls, depth - 1, headers=headers))

    return list(set(endpoints))  # Deduplicate results

def save_to_file(endpoints, output_file):
    """Save the endpoints to a file."""
    try:
        with open(output_file, "w", encoding="utf-8") as file:
            file.write("\n".join(endpoints))
        print(f"{Fore.GREEN}[+] Endpoints saved to {output_file}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[-] Error saving to file: {e}{Style.RESET_ALL}")

def main():
    parser = argparse.ArgumentParser(description="Ultra-Advanced API Endpoint Extractor")
    parser.add_argument("-u", "--url", required=True, help="Target URL to scrape")
    parser.add_argument("-o", "--output", help="Output file to save the endpoints")
    parser.add_argument("-d", "--depth", type=int, default=1, help="Depth of link navigation (default: 1)")
    parser.add_argument("--headers", help="Custom headers as a JSON string (e.g., '{\"User-Agent\": \"CustomBot\"}')")
    args = parser.parse_args()

    url = args.url
    output_file = args.output
    depth = args.depth
    headers = eval(args.headers) if args.headers else None

    print(f"{Fore.BLUE}[+] Starting endpoint extraction for: {url}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}[+] Navigation depth: {depth}{Style.RESET_ALL}")

    visited_urls = set()
    endpoints = scrape_page_and_find_endpoints(url, visited_urls, depth=depth, headers=headers)

    if endpoints:
        print(f"\n{Fore.GREEN}[+] Found {len(endpoints)} endpoints:{Style.RESET_ALL}")
        for endpoint in endpoints:
            print(f"  {endpoint}")

        if output_file:
            save_to_file(endpoints, output_file)
    else:
        print(f"{Fore.RED}[-] No endpoints found.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
