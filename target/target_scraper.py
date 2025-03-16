import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import re
import argparse

def scrape_target_products(url, output_dir="results", search_term="", items_per_page=24, max_pages=12):
    """
    Scrape products from Target using URL-based pagination with the Nao parameter
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Set output filename based on search term
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    if not search_term:
        search_term = "target_products"
    output_file = os.path.join(output_dir, f"target_{search_term.replace(' ', '_')}_{timestamp}.json")
    print(f"Starting scrape for URL: {url}")
    
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Disable WebGL to avoid deprecation warnings
    chrome_options.add_argument("--disable-webgl")
    
    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    
    all_products = []
    unique_products = {}
    
    try:
        # Navigate to the URL
        print(f"Loading URL: {url}")
        driver.get(url)
        
        # Handle store selection
        try:
            print("Checking for store selection dialog...")
            store_selector = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//button[contains(@data-test, "storeId-")]'))
            )
            print("Store selection dialog found, clicking...")
            store_selector.click()
            print("Selected store successfully")
            time.sleep(1)  # Reduced wait time
        except:
            print("No store selection dialog detected")
        
        # Get total number of pages - with maximum limit
        total_pages = min(get_total_pages(driver), max_pages)
        print(f"Found {total_pages} pages to scrape (limited to {max_pages})")
        
        # Process each page using the Nao parameter for pagination
        for page_num in range(1, total_pages + 1):
            print(f"Processing page {page_num} of {total_pages}")
            
            # For the first page, we're already there
            if page_num > 1:
                # Calculate the Nao value based on items per page
                nao_value = (page_num - 1) * items_per_page
                
                # Construct the URL with the Nao parameter
                page_url = url
                if '?' in page_url:
                    if 'Nao=' in page_url:
                        page_url = re.sub(r'Nao=\d+', f'Nao={nao_value}', page_url)
                    else:
                        page_url = f"{url}&Nao={nao_value}"
                else:
                    page_url = f"{url}?Nao={nao_value}"
                
                print(f"Navigating directly to page URL: {page_url}")
                driver.get(page_url)
                time.sleep(1)  # Reduced wait time
            
            # Scroll down the page to trigger lazy loading
            scroll_page(driver)
            
            # Extract products from current page
            page_products = extract_products(driver)
            
            if page_products:
                # Add only unique products based on title
                new_unique_count = 0
                for product in page_products:
                    if 'title' in product and product['title']:
                        product_key = product['title'].strip()
                        if product_key not in unique_products:
                            # Add store information
                            product['store'] = 'target'
                            unique_products[product_key] = product
                            all_products.append(product)
                            new_unique_count += 1
                
                print(f"Extracted {len(page_products)} products from page {page_num}, {new_unique_count} unique")
            else:
                print(f"No products found on page {page_num}")
                
                # If we hit a page with no products, it might be the real end
                if page_num > 1:
                    print("Hit a page with no products, ending scrape")
                    break
            
            # Save progress after each page
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_products, f, indent=2)
        
        # Save the final results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_products, f, indent=2)
        print(f"Completed scraping. Total unique products: {len(all_products)}")
        
    except Exception as e:
        print(f"Error during scraping: {e}")
        
        # Save any products we've collected so far
        if all_products:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_products, f, indent=2)
            print(f"Saved {len(all_products)} products to {output_file} before error")
    
    finally:
        try:
            driver.quit()
        except:
            pass
    
    return all_products

def get_total_pages(driver):
    """
    Extract the total number of pages from the pagination element with improved accuracy
    """
    try:
        # Wait for pagination element to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-test="pagination"]'))
        )
        
        # First try JSON data in page source - more reliable
        html_source = driver.page_source
        total_pages_match = re.search(r'"totalPages":(\d+)', html_source)
        if total_pages_match:
            total = int(total_pages_match.group(1))
            print(f"Found totalPages in page source: {total}")
            return total
        
        # Look for "page X of Y" text
        page_text = driver.find_elements(By.XPATH, '//*[contains(text(), "page") and contains(text(), "of")]')
        for element in page_text:
            text = element.text.strip()
            page_match = re.search(r'page\s+\d+\s+of\s+(\d+)', text.lower())
            if page_match:
                return int(page_match.group(1))
        
        # Check the last visible page number button
        page_buttons = driver.find_elements(By.CSS_SELECTOR, 'div[data-test="pagination"] button')
        max_page = 1
        
        for button in page_buttons:
            button_text = button.text.strip()
            if button_text.isdigit():
                page_num = int(button_text)
                max_page = max(max_page, page_num)
        
        if max_page > 1:
            # Check if there's also a "next" button, which may indicate more pages
            next_buttons = [b for b in page_buttons if b.get_attribute("aria-label") == "next page"]
            if next_buttons:
                # Return a reasonable default rather than a huge number
                return 12  # Target typically has around 12 pages max
            return max_page
            
        # Default: single page
        return 1
            
    except Exception as e:
        print(f"Error getting total pages: {e}")
        return 1  # Default to 1 page

def scroll_page(driver):
    """
    More efficient page scrolling
    """
    try:
        # Get the page height
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        # Faster scrolling with fewer pauses
        scroll_positions = [0.25, 0.5, 0.75, 1.0]  # Scroll in 4 steps
        
        for position in scroll_positions:
            # Scroll to percentage of page
            driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {position});")
            time.sleep(0.2)  # Short delay
    except Exception as e:
        print(f"Error during page scrolling: {e}")

def extract_products(driver):
    """
    Extract product data from the current page - optimized version
    """
    products = []
    
    try:
        # Try one reliable selector first before falling back to BeautifulSoup
        try:
            product_elements = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-test="@web/site-top-of-funnel/ProductCardWrapper"]'))
            )
        except TimeoutException:
            print("Primary product selector not found, trying alternatives")
        
        # Get the page source and parse with BeautifulSoup
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Try different product container selectors in order of reliability
        selectors = [
            'div[data-test="@web/site-top-of-funnel/ProductCardWrapper"]',
            'div[data-test="product-card"]', 
            'li[data-test="groceries-product-card"]',
            'div[class*="product-card"]',
            'div[class*="ProductCard"]'
        ]
        
        product_containers = []
        for selector in selectors:
            product_containers = soup.select(selector)
            if product_containers:
                print(f"Found {len(product_containers)} product containers using selector: {selector}")
                break
        
        # Fallback: try to find product links
        if not product_containers:
            product_links = soup.select('a[href^="/p/"]')
            for link in product_links:
                parent = link.find_parent('div')
                if parent and parent not in product_containers:
                    product_containers.append(parent)
            print(f"Found {len(product_containers)} product containers via product links")
        
        # Extract product data
        for container in product_containers:
            product = {}
            
            # Title
            title_selectors = [
                'a[data-test="product-title"] .styles_ndsTruncate__GRSDE',
                '.styles_ndsTruncate__GRSDE',
                '[class*="Truncate"]',
                'h2, h3, h4',
                'a[href*="/p/"]'
            ]
            
            for selector in title_selectors:
                title_elem = container.select_one(selector)
                if title_elem:
                    product['title'] = title_elem.get('title', '').strip() or title_elem.text.strip()
                    break
            
            # Price
            price_selectors = [
                'span[data-test="current-price"]',
                '[class*="price"]', 
                '[class*="Price"]'
            ]
            
            for selector in price_selectors:
                price_elem = container.select_one(selector)
                if price_elem:
                    price_text = price_elem.text.strip()
                    if '$' in price_text and any(c.isdigit() for c in price_text):
                        product['price'] = price_text
                        break
            
            # Get URL and TCIN
            product_link = container.select_one('a[href*="/p/"]')
            if product_link:
                href = product_link.get('href', '')
                product['url'] = 'https://www.target.com' + href if href.startswith('/') else href
                
                # Extract TCIN
                tcin_match = re.search(r'/A-(\d+)', href)
                if tcin_match:
                    product['tcin'] = tcin_match.group(1)
            
            # Only add products with at least a title
            if 'title' in product and product['title']:
                products.append(product)
                
    except Exception as e:
        print(f"Error extracting products: {e}")
    
    return products

if __name__ == "__main__":
    # Simple command line input for search term
    search_term = input("Enter search term (e.g., 'primer', 'foundation'): ")
    
    # Construct search URL
    search_url = f"https://www.target.com/s?searchTerm={search_term.replace(' ', '+')}"
    
    # Run the scraper
    products = scrape_target_products(
        url=search_url,
        output_dir="results",
        search_term=search_term,
        max_pages=12
    )
    
    print(f"Scraped {len(products)} Target products for '{search_term}'")
