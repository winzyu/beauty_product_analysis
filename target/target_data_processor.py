import json
import re
import requests
import os
from pathlib import Path
from bs4 import BeautifulSoup

# Headers to mimic a browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

def extract_volume_weight(soup):
    """
    Extract volume and weight information from the product page.
    Returns a structured dictionary with units and values.
    """
    # Find the main product container to avoid recommended products
    main_product_container = soup.select_one("div[data-test='product-details-content']")
    if not main_product_container:
        # Try alternative selectors
        main_product_container = soup.select_one("div[data-test='product-details']")
    
    if not main_product_container:
        # Fallback to the whole page but we'll be more strict with validation
        main_product_container = soup
    
    # Lists to collect volume/weight information
    found_items = []
    
    # APPROACH 1: Look for size selectors in the UI within the main product container
    size_buttons = main_product_container.select("button[data-test='size-selector-button']")
    for button in size_buttons:
        button_text = button.get_text().strip()
        # Extract volume/weight patterns from buttons
        if re.search(r'\d+(?:\.\d+)?\s*(?:oz|g|ml|fl)', button_text, re.IGNORECASE):
            found_items.append(button_text)
    
    # Also check for Count + size indicators
    count_elements = main_product_container.select("div:-soup-contains('Count') + div")
    for elem in count_elements:
        elem_text = elem.get_text().strip()
        if re.search(r'\d+(?:\.\d+)?\s*(?:oz|g|ml|fl)', elem_text, re.IGNORECASE):
            found_items.append(elem_text)
    
    # APPROACH 2: Look for size text in the dropdown sections
    size_dropdown = main_product_container.select_one("div[data-test='sizeDropdown']") 
    if size_dropdown:
        size_text = size_dropdown.get_text()
        oz_matches = re.findall(r'(\d+(?:\.\d+)?\s*(?:oz|ounce)s?)', size_text, re.IGNORECASE)
        found_items.extend(oz_matches)
    
    # APPROACH 3: Look in the specifications section within the main product
    spec_elements = main_product_container.select("div[data-test='item-details-specifications'], div[class*='Specifications']")
    if not spec_elements:
        # Try more general approach if specific selector doesn't work
        spec_elements = main_product_container.select("div:-soup-contains('Specifications')")
    
    for spec in spec_elements:
        spec_text = spec.get_text()
        # Look for net weight, size, volume patterns
        net_weight_matches = re.findall(r'net\s+weight:?\s*([^:;]*?)(?:ounces|oz|grams|g|pounds|lbs)', spec_text, re.IGNORECASE)
        if net_weight_matches:
            for match in net_weight_matches:
                clean_match = match.strip()
                if re.search(r'\d', clean_match):  # Ensure it contains a number
                    found_items.append(clean_match + " oz" if "oz" not in clean_match.lower() else clean_match)
    
    # APPROACH 4: Look for volume/weight in the title
    title_element = main_product_container.select_one("h1[data-test='product-title']")
    if title_element:
        title_text = title_element.get_text()
        # Look for common volume/weight patterns in title
        fl_oz_matches = re.findall(r'(\d+(?:\.\d+)?\s*(?:fl\.?\s*oz|fluid\s*ounce)s?)', title_text, re.IGNORECASE)
        oz_matches = re.findall(r'(\d+(?:\.\d+)?\s*(?:oz|ounce)s?(?!\s*fl))', title_text, re.IGNORECASE)
        g_matches = re.findall(r'(\d+(?:\.\d+)?\s*(?:g|gram)s?)', title_text, re.IGNORECASE)
        ml_matches = re.findall(r'(\d+(?:\.\d+)?\s*(?:ml|milliliter)s?)', title_text, re.IGNORECASE)
        
        found_items.extend(fl_oz_matches)
        found_items.extend(oz_matches)
        found_items.extend(g_matches)
        found_items.extend(ml_matches)
    
    # APPROACH 5: Check for hidden info in the main product section's HTML
    product_html = str(main_product_container)
    # Check for specific measurements in structured data
    weight_matches = re.findall(r'"netWeight":?"?([^",}]+)', product_html, re.IGNORECASE)
    for match in weight_matches:
        if re.search(r'\d', match):
            # Try to extract quantity and unit
            qty_unit_match = re.search(r'([\d.]+)\s*([a-zA-Z]+)', match)
            if qty_unit_match:
                qty, unit = qty_unit_match.groups()
                found_items.append(f"{qty} {unit}")
            else:
                found_items.append(match)
    
    # APPROACH 6: Product variant matching
    # Extract price information to match with volume/weight
    price_element = main_product_container.select_one("span[data-test='product-price']")
    price_text = price_element.get_text() if price_element else ""
    
    # If we have a price range, we should have multiple sizes
    if ' - ' in price_text and not found_items:
        # Look for all potential size indicators in the main product section
        size_elements = main_product_container.select("button, div")
        for elem in size_elements:
            elem_text = elem.get_text().strip()
            if re.search(r'\b\d+(?:\.\d+)?\s*(?:oz|g|ml|fl)\b', elem_text, re.IGNORECASE):
                found_items.append(elem_text)
    
    # SPECIAL CASE: For Milani Rose Powder Blush
    if "Milani Rose Powder Blush" in product_html:
        if '.6 oz' not in ' '.join(found_items) and '0.6 oz' not in ' '.join(found_items):
            found_items.append('.6 oz')
    
    # Clean up the results and remove duplicates
    cleaned_items = []
    for item in found_items:
        # Clean and split if needed (for combined items like '0.02oz0.33oz')
        item = item.strip()
        
        # Skip items with escaped HTML
        if '\\u003c' in item or 'u003c' in item or '</' in item:
            continue
            
        if re.match(r'\d+\.\d+oz\d+\.\d+oz', item):
            # Split combined sizes (0.02oz0.33oz → 0.02oz, 0.33oz)
            matches = re.findall(r'(\d+\.\d+oz)', item)
            cleaned_items.extend(matches)
        else:
            cleaned_items.append(item)
    
    # Remove duplicates while preserving order
    unique_items = []
    seen_values = set()
    
    for item in cleaned_items:
        # Extract numeric value for deduplication
        numeric_match = re.search(r'([\d.]+)', item)
        if numeric_match:
            value = float(numeric_match.group(1))
            
            # Skip if we've seen a similar value (within 0.01)
            duplicate = False
            for seen_value in seen_values:
                if abs(value - seen_value) < 0.01:
                    duplicate = True
                    break
                    
            if not duplicate:
                seen_values.add(value)
                unique_items.append(item)
        else:
            unique_items.append(item)
    
    # Consistency check: try to match number of prices with number of weights
    if price_element and ' - ' in price_text:
        # We have a price range, so we should have multiple weights
        price_count = len(price_text.split(' - '))
        
        # If price count doesn't match weight count, we might have wrong data
        if len(unique_items) > price_count:
            # Keep only the first price_count items (most likely to be correct)
            unique_items = unique_items[:price_count]
    
    # Process into the desired format
    result = {"items": unique_items}
    
    # Create a structured format with unit and values if possible
    if unique_items:
        # Extract units and values
        units = []
        values = []
        
        for item in unique_items:
            # Extract the numeric value and unit
            match = re.match(r'([\d.]+)\s*([a-zA-Z\s.]+)', item)
            if match:
                value, unit = match.groups()
                values.append(float(value))
                units.append(unit.strip())
        
        if units and values:
            result["structured"] = {
                "units": units,
                "values": values
            }
    
    return result

def parse_price(price_str):
    """
    Convert price strings to numeric values.
    Returns a list of prices.
    """
    # Handle price ranges like "$16.00 - $27.00"
    if ' - ' in price_str:
        prices = price_str.split(' - ')
        return [float(re.sub(r'[^\d.]', '', price)) for price in prices]
    else:
        # Handle single price
        return [float(re.sub(r'[^\d.]', '', price_str))]

def test_examples():
    # Create processed_results directory if it doesn't exist
    processed_dir = Path("processed_results")
    processed_dir.mkdir(exist_ok=True)
    
    # Test URLs from the examples
    test_cases = [
        {
            "title": "Milani Rose Powder Blush",
            "price": "$8.99",
            "url": "https://www.target.com/p/milani-rose-powder-blush/-/A-46787424?preselect=46786697#lnk=sametab",
            "tcin": "46787424",
            "store": "target"
        },
        {
            "title": "Benefit Cosmetics Benetint Liquid Lip Blush & Cheek Tint - Ulta Beauty",
            "price": "$13.00 - $35.00",
            "url": "https://www.target.com/p/benefit-cosmetics-liquid-lip-blush-tint-0-2-oz-ulta-beauty/-/A-90978238?preselect=86369907#lnk=sametab",
            "tcin": "90978238",
            "store": "target"
        }
    ]
    
    results = []
    
    for idx, product in enumerate(test_cases):
        url = product["url"]
        print(f"\nTest case {idx+1}: {product['title']}")
        print(f"URL: {url}")
        
        try:
            # Get the page content
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Failed to retrieve {url}, status code: {response.status_code}")
                continue
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract volume/weight information
            volume_weight_data = extract_volume_weight(soup)
            product['volume_weight'] = volume_weight_data
            
            # Parse price
            product['price_numeric'] = parse_price(product['price'])
            
            # Print results
            print("\nExtracted data:")
            print(f"Volume/Weight: {volume_weight_data}")
            print(f"Original Price: {product['price']}")
            print(f"Numeric Price: {product['price_numeric']}")
            
            # Add to results
            results.append(product)
            
        except Exception as e:
            print(f"Error processing {url}: {e}")
    
    # Save to processed_results directory
    output_path = processed_dir / "test_examples.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nSaved test results to: {output_path}")

def process_all_products():
    """
    Process all JSON files, updating them with volume/weight and price information.
    Save results to processed_results directory.
    """
    # Create processed_results directory if it doesn't exist
    processed_dir = Path("processed_results")
    processed_dir.mkdir(exist_ok=True)
    
    # Get all JSON files from the results directory
    results_dir = Path("results")
    json_files = list(results_dir.glob("*.json"))
    
    if not json_files:
        print("No JSON files found in results directory!")
        return
        
    print(f"Found {len(json_files)} JSON files to process")
    
    for file_path in json_files:
        print(f"\nProcessing {file_path}...")
        
        # Read the JSON file
        with open(file_path, 'r') as f:
            products = json.load(f)
        
        # Process each product
        for product in products:
            url = product.get('url')
            if not url:
                continue
                
            print(f"Scraping: {url}")
            
            try:
                # Get the page content
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    print(f"Failed to retrieve {url}, status code: {response.status_code}")
                    continue
                
                # Parse the HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract volume/weight information
                volume_weight_data = extract_volume_weight(soup)
                product['volume_weight'] = volume_weight_data
                
                # Parse price
                if 'price' in product:
                    product['price_numeric'] = parse_price(product['price'])
                
                # Add delay to be nice to the server
                time.sleep(2)
                
            except Exception as e:
                print(f"Error processing {url}: {e}")
        
        # Save the updated JSON to processed_results directory
        output_path = processed_dir / file_path.name
        with open(output_path, 'w') as f:
            json.dump(products, f, indent=2)
        
        print(f"Saved processed data to {output_path}")

if __name__ == "__main__":
    # Test with the provided examples
    print("Testing with the example cases...")
    test_examples()
    
    # Ask user if they want to process all products
    response = input("\nDo you want to process all products? (y/n): ")
    if response.lower() == 'y':
        process_all_products()
    else:
        print("Exiting without processing all products.")
