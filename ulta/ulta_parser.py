import re
import json
import os

def parse_ulta_output(output_file):
    """Parse the Ulta scraped output and convert it to JSON format."""
    # Read the file content
    with open(output_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Identify product categories
    category_sections = []
    category_pattern = r"Starting (.*?) scraper"
    category_matches = re.finditer(category_pattern, content)
    
    indices = []
    for match in category_matches:
        category = match.group(1).strip().lower().replace(' ', '_')
        indices.append((match.start(), category))
    
    # Add an end index
    indices.append((len(content), None))
    
    # Extract each category section
    for i in range(len(indices) - 1):
        start, category = indices[i]
        end = indices[i+1][0]
        section_text = content[start:end]
        category_sections.append((category, section_text))
    
    # Process each category section
    results = {}
    for category, section_text in category_sections:
        products = extract_products(section_text)
        if products:
            results[category] = products
    
    return results

def extract_products(section_text):
    """Extract individual product information from a section of text."""
    products = []
    
    # Patterns to extract product information
    brand_pattern = r"Found brand: ([^\n]+)"
    name_pattern = r"Found product name: ([^\n]+)"
    price_pattern = r"Found price: \$([0-9.]+)"
    review_pattern = r"Found review count: ([0-9]+)"
    color_pattern = r"Found color options: ([0-9]+)"
    exclusive_pattern = r"Product is exclusive"
    
    # Extract all instances of product information
    brands = [m.group(1).strip().replace("Â", "") for m in re.finditer(brand_pattern, section_text)]
    names = [m.group(1).strip() for m in re.finditer(name_pattern, section_text)]
    prices = [float(m.group(1)) for m in re.finditer(price_pattern, section_text)]
    
    # Optional attributes
    reviews = [int(m.group(1)) for m in re.finditer(review_pattern, section_text)]
    colors = [int(m.group(1)) for m in re.finditer(color_pattern, section_text)]
    exclusives = [m.start() for m in re.finditer(exclusive_pattern, section_text)]
    
    # Find the minimum length of the essential attributes
    min_length = min(len(brands), len(names), len(prices))
    
    # Create products from the extracted information
    for i in range(min_length):
        product = {
            "store": "ulta",
            "brand": brands[i],
            "name": names[i],
            "title": f"{brands[i]} {names[i]}",
            "price": prices[i]
        }
        
        # Add optional attributes if available
        if i < len(reviews):
            product["review_count"] = reviews[i]
        
        if i < len(colors):
            product["color_options"] = colors[i]
        
        # Check if this product is likely to be exclusive
        # This is a heuristic based on the position of "Product is exclusive" in the text
        for exclusive_pos in exclusives:
            # If "Product is exclusive" appears after the brand and before the next brand,
            # mark this product as exclusive
            brand_pos = section_text.find(f"Found brand: {brands[i]}")
            next_brand_pos = float('inf')
            if i + 1 < len(brands):
                next_brand_pos = section_text.find(f"Found brand: {brands[i+1]}")
            
            if brand_pos < exclusive_pos < next_brand_pos:
                product["exclusive"] = True
                break
        
        products.append(product)
    
    return products

def save_to_json_files(results, output_dir):
    """Save results to JSON files, one per category."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    saved_files = []
    for category, products in results.items():
        if products:
            filename = f"ulta_{category}.json"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2)
            
            saved_files.append(filepath)
            print(f"Saved {len(products)} products to {filepath}")
    
    return saved_files

if __name__ == "__main__":
    # Path to the extracted output
    output_file = os.path.join("extracted_output.txt")
    
    # Path for the JSON output files
    output_dir = os.path.join("results")
    
    if os.path.exists(output_file):
        results = parse_ulta_output(output_file)
        if results:
            saved_files = save_to_json_files(results, output_dir)
            print(f"Successfully saved {len(saved_files)} category files.")
        else:
            print("No products found in the output.")
    else:
        print(f"Output file not found: {output_file}")
