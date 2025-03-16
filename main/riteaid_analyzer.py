import requests
from bs4 import BeautifulSoup

# Base URL for Rite Aid search
url = "https://www.riteaid.com/shop/catalogsearch/result/?q=primer"

# Headers
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

print(f"Accessing URL: {url}")

# Get the page
response = requests.get(url, headers=headers)
print(f"Status Code: {response.status_code}")

# Save the HTML
with open("riteaid_page.html", "w", encoding="utf-8") as f:
    f.write(response.text)
print("Saved HTML to riteaid_page.html")

# Parse the HTML
soup = BeautifulSoup(response.text, 'html.parser')

# Print the page title
print(f"\nPage Title: {soup.title.text}")

# Check if we're getting search results or a different page
if "Search results for" in soup.title.text:
    print("✓ This appears to be a search results page")
else:
    print("⚠ This does not appear to be a search results page")

# Look for product containers - try various selectors
selectors = [
    '.item.product.product-item',
    '.product-item',
    '.product',
    '[data-product-id]',
    '.products-grid .item'
]

print("\nChecking for product containers:")
for selector in selectors:
    elements = soup.select(selector)
    if elements:
        print(f"✓ Found {len(elements)} elements with selector: '{selector}'")
        
        # Analyze the first element
        first = elements[0]
        print("\nFirst product container:")
        print(f"Classes: {first.get('class')}")
        print(f"Data attributes: {[attr for attr in first.attrs.keys() if attr.startswith('data-')]}")
        
        # Look for product name
        name_element = first.select_one('.product-item-link')
        if name_element:
            print(f"Product name: {name_element.text.strip()}")
        
        # Look for price
        price_element = first.select_one('.price')
        if price_element:
            print(f"Price: {price_element.text.strip()}")
            
        break
else:
    print("❌ No product containers found with common selectors")
    
    # Try to find any element that might contain a price
    price_pattern = soup.find_all(string=lambda text: "$" in text)
    if price_pattern:
        print(f"\nFound {len(price_pattern)} elements containing '$'")
        for i, p in enumerate(price_pattern[:5]):
            print(f"{i+1}. {p.strip()}")
