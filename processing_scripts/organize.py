import os
import json
import re
import shutil
from pathlib import Path

def extract_min_price(price_str):
    """Extract minimum price from a price string, handling ranges like '9.99 - 15.99'"""
    if isinstance(price_str, (int, float)):
        return float(price_str)
    
    # Remove currency symbols
    price_str = price_str.replace('$', '')
    
    # Check if it's a range
    if '-' in price_str:
        prices = [float(p.strip()) for p in price_str.split('-')]
        return min(prices)
    
    # Try to convert to float
    try:
        return float(price_str)
    except ValueError:
        print(f"Warning: Could not parse price {price_str}, defaulting to 9999")
        return 9999.0  # Default high value for unparseable prices

def process_target_data(file_path, output_dir):
    """Process Target data files"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Standardize data format
    processed_data = []
    for item in data:
        processed_data.append({
            "store": "target",
            "name": item.get("title", "Unknown"),
            "price": extract_min_price(item.get("price", "9999"))
        })
    
    # Sort by price
    processed_data.sort(key=lambda x: x["price"])
    
    # Write to output file
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"target_{os.path.basename(file_path).split('_')[1].split('.')[0]}.json")
    with open(output_file, 'w') as f:
        json.dump(processed_data, f, indent=2)

def process_riteaid_data(file_path, output_dir):
    """Process RiteAid data files"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Standardize data format
    processed_data = []
    if "products" in data:
        for item in data["products"]:
            processed_data.append({
                "store": "riteaid",
                "name": item.get("name", "Unknown"),
                "price": extract_min_price(item.get("price", 9999))
            })
    
    # Sort by price
    processed_data.sort(key=lambda x: x["price"])
    
    # Write to output file
    os.makedirs(output_dir, exist_ok=True)
    category = data.get("category", os.path.basename(file_path).split('_')[1].split('.')[0])
    output_file = os.path.join(output_dir, f"riteaid_{category}.json")
    with open(output_file, 'w') as f:
        json.dump(processed_data, f, indent=2)

def process_ulta_data(file_path, output_dir):
    """Process Ulta data files"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Standardize data format
    processed_data = []
    for item in data:
        processed_data.append({
            "store": "ulta",
            "name": item.get("title", item.get("name", "Unknown")),
            "price": extract_min_price(item.get("price", 9999))
        })
    
    # Sort by price
    processed_data.sort(key=lambda x: x["price"])
    
    # Write to output file
    os.makedirs(output_dir, exist_ok=True)
    category = os.path.basename(file_path).split('_')[1].split('.')[0] if '_' in os.path.basename(file_path) else os.path.basename(file_path).split('.')[0]
    output_file = os.path.join(output_dir, f"ulta_{category}.json")
    with open(output_file, 'w') as f:
        json.dump(processed_data, f, indent=2)

def main():
    # Create output directory structure
    base_dir = "sorted_data"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    
    # Create store directories
    store_dirs = {
        "target": os.path.join(base_dir, "target"),
        "riteaid": os.path.join(base_dir, "riteaid"),
        "ulta": os.path.join(base_dir, "ulta")
    }
    
    # Create category directories
    categories = [
        "blush", "concealer", "eyebrow_gel", "foundation", 
        "lip_gloss", "powder", "primer", "setting_spray"
    ]
    
    for store, store_dir in store_dirs.items():
        for category in categories:
            os.makedirs(os.path.join(store_dir, category), exist_ok=True)
    
    # Process Target files
    target_dir = "target/results"
    for category in categories:
        category_dir = os.path.join(target_dir, category)
        if os.path.exists(category_dir):
            for file in os.listdir(category_dir):
                if file.endswith(".json"):
                    file_path = os.path.join(category_dir, file)
                    output_dir = os.path.join(store_dirs["target"], category)
                    process_target_data(file_path, output_dir)
    
    # Process RiteAid files
    riteaid_dir = "riteaid/results"
    for category in categories:
        category_dir = os.path.join(riteaid_dir, category)
        if os.path.exists(category_dir):
            for file in os.listdir(category_dir):
                if file.endswith(".json"):
                    file_path = os.path.join(category_dir, file)
                    output_dir = os.path.join(store_dirs["riteaid"], category)
                    process_riteaid_data(file_path, output_dir)
    
    # Process Ulta files
    ulta_dir = "ulta/results"
    for category in categories:
        category_dir = os.path.join(ulta_dir, category)
        if os.path.exists(category_dir):
            for file in os.listdir(category_dir):
                if file.endswith(".json"):
                    file_path = os.path.join(category_dir, file)
                    output_dir = os.path.join(store_dirs["ulta"], category)
                    process_ulta_data(file_path, output_dir)
    
    print(f"Data organization complete. Output directory: {base_dir}")

if __name__ == "__main__":
    main()
