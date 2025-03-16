import requests
import json
from urllib.parse import urlparse, parse_qs

# Target search URL
url = "https://www.target.com/s?searchTerm=primer"

# Headers
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

# Get the page
response = requests.get(url, headers=headers)
print(f"Status Code: {response.status_code}")

# Save the HTML
with open("target_page.html", "w", encoding="utf-8") as f:
    f.write(response.text)
print("Saved HTML to target_page.html")

# Now look for API endpoints in the HTML
import re

redsky_pattern = re.compile(r'(https://redsky\.target\.com[^"\']*)')
api_matches = redsky_pattern.findall(response.text)

if api_matches:
    print(f"\nFound {len(api_matches)} potential Redsky API endpoints:")
    unique_apis = set(api_matches)
    for i, api in enumerate(list(unique_apis)[:10]):
        print(f"\n{i+1}. {api}")
        
        # Parse the URL
        parsed_url = urlparse(api)
        params = parse_qs(parsed_url.query)
        
        # Check if this looks like a product search endpoint
        if "key" in params and ("searchTerm" in params or "keyword" in params or "q" in params):
            print("⭐ This looks like a search endpoint!")
            print(f"Endpoint: {parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}")
            print("Parameters:")
            for key, value in params.items():
                print(f"  - {key}: {value[0]}")
else:
    print("No Redsky API endpoints found")

# Also check for any other API endpoints
general_api_pattern = re.compile(r'(https://api\.target\.com[^"\']*)')
general_matches = general_api_pattern.findall(response.text)

if general_matches:
    print(f"\nFound {len(general_matches)} potential Target API endpoints:")
    unique_apis = set(general_matches)
    for i, api in enumerate(list(unique_apis)[:5]):
        print(f"\n{i+1}. {api}")
        
        # Parse the URL
        parsed_url = urlparse(api)
        print(f"Endpoint: {parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}")
