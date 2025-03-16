#!/usr/bin/env python3
import json
import os
import sys
import re
from pathlib import Path

def process_riteaid_output(input_file):
    """
    Process RiteAid notebook output text file and separate by category
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get current timestamp for file naming
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Find all category blocks using regex pattern
        category_blocks = re.finditer(r'([\w\s]+)\s+\((\d+)\s+items\):\s*\n[-]+\s*([\s\S]+?)(?=\n\n[\w\s]+\s+\(\d+\s+items\):|$)', content)
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        results_dir = os.path.join(script_dir, "results")
        os.makedirs(results_dir, exist_ok=True)
        
        categories_processed = []
        
        for match in category_blocks:
            category_name = match.group(1).strip()
            item_count = int(match.group(2))
            product_text = match.group(3).strip()
            
            # Skip if already processed (avoid duplicates)
            if category_name in categories_processed:
                continue
                
            categories_processed.append(category_name)
            
            # Process products in this category
            products = []
            for line in product_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # Parse product details
                match = re.search(r'(.*?)\s+-\s+\$([0-9.]+)$', line)
                if match:
                    name = match.group(1).strip()
                    price = float(match.group(2))
                    
                    # Extract size if present
                    size_match = re.search(r'(.*?),\s+([\d.]+\s+[a-zA-Z. ]+)$', name)
                    if size_match:
                        product_name = size_match.group(1).strip()
                    else:
                        product_name = name
                    
                    products.append({
                        "name": product_name,
                        "price": price,
                        "store": "RiteAid"
                    })
            
            # Normalize category name for filename
            filename_category = category_name.lower().replace(' ', '_')
            
            # Create result for this category
            result = {
                "store": "RiteAid",
                "category": filename_category,
                "timestamp": timestamp,
                "products": products
            }
            
            # Save to file
            output_file = os.path.join(results_dir, f"riteaid_{filename_category}_{timestamp}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
                
            print(f"Saved {len(products)} products for category '{category_name}' to {output_file}")
        
        return len(categories_processed)
    
    except Exception as e:
        print(f"Error processing RiteAid file: {str(e)}")
        return 0

def main():
    # Get directory where this script is located (should be riteaid folder)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Look for extracted outputs in the extracted_outputs directory
    outputs_dir = os.path.join(script_dir, "extracted_outputs")
    
    if not os.path.exists(outputs_dir):
        # Try to create it if it doesn't exist
        try:
            os.makedirs(outputs_dir)
            print(f"Created directory: {outputs_dir}")
        except Exception as e:
            print(f"Error creating directory {outputs_dir}: {str(e)}")
            return
    
    # Look for the first text output file
    input_file = None
    for file in os.listdir(outputs_dir):
        if file.endswith("_outputs.txt"):
            input_file = os.path.join(outputs_dir, file)
            break
    
    if not input_file:
        print("No output text file found. Please run the notebook output extractor first.")
        return
    
    # Process the file and separate by category
    num_categories = process_riteaid_output(input_file)
    print(f"Processed {num_categories} product categories from RiteAid data")

if __name__ == "__main__":
    main()

