"""
Makeup Price Comparison Tool for Target and Rite Aid

This script compares prices of makeup products between Target and Rite Aid
to find the cheapest option for each product type.
"""

import requests
import json
import re
import random
import string
import time
from bs4 import BeautifulSoup
import pandas as pd

###############################################################################
# TARGET API IMPLEMENTATION
###############################################################################

# Base URLs for Target's APIs
REDSKY_SEARCH_URL = "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v1"
TARGET_BASE_URL = "https://www.target.com"

# Headers based on common browser settings
TARGET_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.target.com/s?searchTerm=primer",
    "Origin": "https://www.target.com",
    "Connection": "keep-alive",
}

def generate_visitor_id():
    """Generate a random visitor ID for Target's API."""
    # Create a 32-character hex string (typical format used by Target)
    return ''.join(random.choice(string.hexdigits) for _ in range(32)).upper()

def get_davis_store_id():
    """Get the store ID for Target in Davis, CA."""
    # This is the real Davis store ID
    return "3132"  # Davis, CA Target store ID

def target_extract_products(search_term, page=0, zip_code="95616", visitor_id=None):
    """
    Extract products from Target's Redsky API for a given search term.
    
    Args:
        search_term: The product to search for (e.g., "primer")
        page: Page number (controls the offset)
        zip_code: ZIP code for location-specific results (Davis, CA = 95616)
        visitor_id: Optional visitor ID (will be generated if not provided)
    
    Returns:
        A dictionary with product data and metadata
    """
    # Generate a visitor ID if not provided
    if not visitor_id:
        visitor_id = generate_visitor_id()
    
    # Calculate offset (24 items per page as mentioned in course materials)
    offset = page * 24
    
    # Store ID for the Target store in Davis
    store_id = get_davis_store_id()
    
    # Parameters for the search API based on course materials
    params = {
        "key": "9f36aeafbe60771e321a7cc95a78140772ab3e96",  # API key
        "channel": "WEB",
        "count": 24,
        "default_purchasability_filter": "true",
        "include_sponsored": "true", 
        "offset": offset,
        "page": f"/s/{search_term}",
        "platform": "desktop",
        "pricing_store_id": store_id,
        "scheduled_delivery_store_id": store_id,
        "store_ids": store_id,
        "useragent": "Mozilla/5.0",
        "visitor_id": visitor_id,
        "zip": zip_code
    }
    
    print(f"Searching Target for '{search_term}' (Page {page+1}, Offset: {offset})...")
    
    try:
        # Make request to Target's API
        response = requests.get(
            REDSKY_SEARCH_URL,
            params=params,
            headers=TARGET_HEADERS,
            timeout=10
        )
        
        # Check if request was successful
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Extract product details from the response
                products = []
                
                # Parse products based on known Redsky API structure
                if "data" in data and "search" in data["data"] and "products" in data["data"]["search"]:
                    raw_products = data["data"]["search"]["products"]
                    
                    for product in raw_products:
                        # Extract basic product information
                        product_info = {
                            "store": "Target",
                            "tcin": product.get("tcin"),  # Target's product ID
                            "title": product.get("item", {}).get("product_description", {}).get("title", ""),
                            "description": product.get("item", {}).get("product_description", {}).get("downstream_description", ""),
                            "url": f"{TARGET_BASE_URL}{product.get('item', {}).get('enrichment', {}).get('buy_url', '')}",
                            "upc": product.get("item", {}).get("primary_barcode", ""),
                            "brand": product.get("item", {}).get("product_brand", {}).get("brand", ""),
                        }
                        
                        # Extract price information
                        price_data = product.get("price", {})
                        product_info["price"] = price_data.get("current_retail", 0)
                        product_info["price_text"] = price_data.get("formatted_current_price", "")
                        product_info["regular_price"] = price_data.get("reg_retail", 0)
                        product_info["on_sale"] = price_data.get("is_current_price_type_sale", False)
                        
                        # Extract image information
                        image_data = product.get("item", {}).get("enrichment", {}).get("images", {})
                        product_info["image_url"] = image_data.get("primary_image_url", "")
                        
                        # Get availability information
                        avail_data = product.get("fulfillment", {})
                        product_info["in_stock"] = avail_data.get("is_out_of_stock_in_all_store_locations", False) == False
                        
                        products.append(product_info)
                
                # Prepare the result dictionary with metadata
                result = {
                    "search_term": search_term,
                    "page": page,
                    "products": products,
                    "total_results": data.get("data", {}).get("search", {}).get("total_results", 0),
                    "total_pages": (data.get("data", {}).get("search", {}).get("total_results", 0) + 23) // 24,
                    "visitor_id": visitor_id,  # Return visitor_id for pagination
                }
                
                print(f"Found {len(products)} products at Target")
                return result
                
            except json.JSONDecodeError:
                print("Response is not valid JSON")
                print(f"Response text snippet: {response.text[:200]}...")
        else:
            print(f"Request failed with status code: {response.status_code}")
            print(f"Response text snippet: {response.text[:200]}...")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    return None

def target_get_all_products(search_term, max_pages=2):
    """Get all products for a search term from Target, up to a maximum number of pages."""
    all_products = []
    visitor_id = generate_visitor_id()
    
    for page in range(max_pages):
        result = target_extract_products(search_term, page=page, visitor_id=visitor_id)
        
        if not result or not result["products"]:
            break
        
        all_products.extend(result["products"])
        
        # Check if we've reached the last page
        if page + 1 >= result["total_pages"]:
            break
        
        # Be nice to the server
        time.sleep(2)
    
    return all_products

###############################################################################
# RITE AID IMPLEMENTATION
###############################################################################

# Base URL for Rite Aid search
RITEAID_BASE_URL = "https://www.riteaid.com"
RITEAID_SEARCH_URL = f"{RITEAID_BASE_URL}/shop/catalogsearch/result/"

# Headers based on common browser settings
RITEAID_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.riteaid.com/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0"
}

def extract_price(price_str):
    """Extract numerical price from string."""
    if not price_str:
        return None
        
    # Use regex to find price patterns
    matches = re.findall(r'\$(\d+\.\d+)', price_str)
    if matches:
        return float(matches[0])
    
    # Try another pattern
    matches = re.findall(r'(\d+\.\d+)', price_str)
    if matches:
        return float(matches[0])
    
    return None

def riteaid_scrape_products(search_term, max_pages=2):
    """
    Scrape product information from Rite Aid search results.
    
    Args:
        search_term: The search term to use (e.g., "primer")
        max_pages: Maximum number of pages to scrape
    
    Returns:
        A list of product dictionaries
    """
    all_products = []
    current_page = 1
    
    while current_page <= max_pages:
        # Construct the URL for the current page
        if current_page == 1:
            url = f"{RITEAID_SEARCH_URL}?q={search_term}"
        else:
            url = f"{RITEAID_SEARCH_URL}?q={search_term}&p={current_page}"
        
        print(f"Scraping page {current_page} for '{search_term}' at Rite Aid...")
        
        try:
            # Get the page
            response = requests.get(url, headers=RITEAID_HEADERS, timeout=10)
            
            # Check if request was successful
            if response.status_code == 200:
                # Parse the HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find product elements
                product_elements = soup.select('.item.product.product-item')
                
                if not product_elements:
                    print("No products found on this page")
                    break
                
                print(f"Found {len(product_elements)} products on page {current_page}")
                
                # Parse each product
                page_products = []
                for element in product_elements:
                    try:
                        product = {}
                        product["store"] = "Rite Aid"
                        
                        # Extract product name
                        name_element = element.select_one('.product-item-link')
                        if name_element:
                            product['title'] = name_element.text.strip()
                            product['url'] = name_element.get('href', '')
                        else:
                            continue  # Skip if no name
                        
                        # Extract price
                        price_element = element.select_one('.price')
                        if price_element:
                            price_text = price_element.text.strip()
                            product['price_text'] = price_text
                            product['price'] = extract_price(price_text)
                        else:
                            continue  # Skip if no price
                        
                        # Extract regular price if available (for sale items)
                        old_price = element.select_one('.old-price .price')
                        if old_price:
                            old_price_text = old_price.text.strip()
                            product['regular_price_text'] = old_price_text
                            product['regular_price'] = extract_price(old_price_text)
                            product['on_sale'] = True
                        else:
                            product['on_sale'] = False
                        
                        # Extract product image
                        img_element = element.select_one('.product-image-photo')
                        if img_element:
                            product['image_url'] = img_element.get('src', '')
                        
                        # Extract brand information if available
                        brand_element = element.select_one('.product-brand')
                        if brand_element:
                            product['brand'] = brand_element.text.strip()
                        
                        # Check if product is in stock
                        stock_element = element.select_one('.stock.unavailable')
                        product['in_stock'] = stock_element is None
                        
                        # Add to the list
                        page_products.append(product)
                    except Exception as e:
                        print(f"Error parsing product: {str(e)}")
                
                # Add products from this page to our collection
                all_products.extend(page_products)
                print(f"Collected {len(all_products)} products from Rite Aid so far")
                
                # Check if there's a next page
                next_page_link = soup.select_one('a.action.next')
                if not next_page_link:
                    print("No next page link found - reached the end")
                    break
                
                # Move to the next page
                current_page += 1
                
                # Be nice to the server
                time.sleep(2)
            else:
                print(f"Failed to retrieve page {current_page}. Status code: {response.status_code}")
                break
                
        except Exception as e:
            print(f"Error: {str(e)}")
            break
    
    return all_products

###############################################################################
# COMBINED FUNCTIONALITY
###############################################################################

def get_cheapest_products(product_types):
    """
    Find the cheapest options for each product type across all stores.
    
    Args:
        product_types: List of makeup product types to search for
    
    Returns:
        DataFrame with the cheapest products
    """
    all_results = []
    
    for product_type in product_types:
        print(f"\n{'='*50}")
        print(f"Searching for {product_type}...")
        print(f"{'='*50}")
        
        # Get products from Target
        print("\n--- Target ---")
        target_products = target_get_all_products(product_type)
        
        # Get products from Rite Aid
        print("\n--- Rite Aid ---")
        riteaid_products = riteaid_scrape_products(product_type)
        
        # Combine all products
        all_products = target_products + riteaid_products
        
        # Filter out products without price
        products_with_price = [p for p in all_products if 'price' in p and p['price'] is not None]
        
        if products_with_price:
            # Sort by price
            sorted_products = sorted(products_with_price, key=lambda x: x['price'])
            
            # Get the cheapest product
            cheapest = sorted_products[0]
            
            # Print the result
            print(f"\nCheapest {product_type}: {cheapest.get('title', 'Unknown')}")
            print(f"Price: ${cheapest.get('price', 'Unknown')}")
            print(f"Store: {cheapest.get('store', 'Unknown')}")
            print(f"URL: {cheapest.get('url', 'Unknown')}")
            
            # Add to results
            all_results.append({
                'product_type': product_type,
                'title': cheapest.get('title', 'Unknown'),
                'price': cheapest.get('price', 0),
                'price_text': cheapest.get('price_text', f"${cheapest.get('price', 0)}"),
                'store': cheapest.get('store', 'Unknown'),
                'url': cheapest.get('url', 'Unknown'),
                'image_url': cheapest.get('image_url', ''),
                'brand': cheapest.get('brand', 'Unknown'),
                'in_stock': cheapest.get('in_stock', True),
                'on_sale': cheapest.get('on_sale', False)
            })
            
            # Save all products for this type to a file for reference
            with open(f"{product_type}_all_products.json", 'w', encoding='utf-8') as f:
                json.dump(products_with_price, f, indent=2)
        else:
            print(f"No products found for {product_type}")
    
    # Create a DataFrame from the results
    if all_results:
        df = pd.DataFrame(all_results)
        
        # Save to CSV
        df.to_csv("cheapest_makeup_products.csv", index=False)
        print("\nResults saved to cheapest_makeup_products.csv")
        
        return df
    else:
        print("No results found")
        return None

def create_html_report(df):
    """Create an HTML report with the results."""
    if df is None or df.empty:
        return "<h1>No results found</h1>"
    
    # Start HTML document
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cheapest Makeup Products</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            table { border-collapse: collapse; width: 100%; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            .price { font-weight: bold; color: #e0115f; }
            .sale { color: #e0115f; font-weight: bold; }
            img { max-width: 100px; max-height: 100px; }
            .button { 
                background-color: #4CAF50; 
                border: none; 
                color: white; 
                padding: 10px 20px; 
                text-align: center; 
                text-decoration: none; 
                display: inline-block; 
                margin: 4px 2px; 
                cursor: pointer; 
                border-radius: 4px; 
            }
            .target { background-color: #cc0000; }
            .riteaid { background-color: #0066cc; }
        </style>
    </head>
    <body>
        <h1>Cheapest Makeup Products in Davis, CA</h1>
    """
    
    # Create table
    html += """
        <table>
            <tr>
                <th>Product Type</th>
                <th>Product</th>
                <th>Image</th>
                <th>Price</th>
                <th>Brand</th>
                <th>Store</th>
                <th>Link</th>
            </tr>
    """
    
    # Add rows to table
    for _, row in df.iterrows():
        store_class = row['store'].lower().replace(' ', '')
        sale_text = " (On Sale!)" if row['on_sale'] else ""
        
        html += f"""
            <tr>
                <td>{row['product_type']}</td>
                <td>{row['title']}</td>
                <td><img src="{row['image_url']}" alt="{row['title']}"></td>
                <td class="price">{row['price_text']}{sale_text}</td>
                <td>{row['brand']}</td>
                <td>{row['store']}</td>
                <td><a href="{row['url']}" target="_blank" class="button {store_class}">Buy Now</a></td>
            </tr>
        """
    
    # Close table and HTML document
    html += """
        </table>
    </body>
    </html>
    """
    
    # Save to file
    with open("cheapest_makeup_products.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print("HTML report saved to cheapest_makeup_products.html")
    return html

if __name__ == "__main__":
    # List of makeup product types to search for
    product_types = [
        "primer",
        "eyebrow gel",
        "concealer",
        "blush",
        "foundation",
        "powder",
        "lip gloss",
        "setting spray"
    ]
    
    # Get the cheapest products
    results = get_cheapest_products(product_types)
    
    # Create an HTML report
    if results is not None:
        create_html_report(results)
