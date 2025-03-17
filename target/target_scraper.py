import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

def set_davis_target_store(search_term):
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-webgl")
    driver = webdriver.Chrome(options=chrome_options)
    
    url = f"https://www.target.com/s?searchTerm={search_term.replace(' ', '+')}"
    driver.get(url)
    time.sleep(2)
    
    try:
        # Click store selector button
        store_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="@web/StoreName/Button"]'))
        )
        store_button.click()
        print("Clicked store selector button")
        
        # Enter Davis zip code
        zip_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "zip-or-city-state"))
        )
        zip_input.clear()
        zip_input.send_keys("95616")
        
        # Click "Look up" button
        lookup_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[text()="Look up"]'))
        )
        lookup_button.click()
        print("Clicked 'Look up' button")
        time.sleep(3)
        
        # Find and click the Davis store (not just the radio button)
        davis_store = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//h4[contains(text(), "Davis")]'))
        )
        davis_store.click()
        print("Clicked on Davis store")
        time.sleep(1)
        
        # Click "Shop this store" button
        shop_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="@web/StoreMenu/ShopThisStoreButton"]'))
        )
        shop_button.click()
        print("Clicked 'Shop this store'")
        
        time.sleep(3)
        return driver
        
    except Exception as e:
        print(f"Error setting Davis store: {e}")
        return driver

def scrape_target_products(search_term, max_pages=12):
    """
    Scrape products from Target.com for a given search term
    """
    # Create output directory
    output_dir = "results"
    os.makedirs(output_dir, exist_ok=True)
    
    # Set output filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"target_{search_term.replace(' ', '_')}_{timestamp}.json")
    
    print(f"Starting scrape for: {search_term}")
    
    # Initialize driver with store selection
    driver = set_davis_target_store(search_term)
    
    all_products = []
    unique_products = {}
    
    try:
        # Get total number of pages
        total_pages = get_page_count(driver)
        total_pages = min(total_pages, max_pages)
        print(f"Found {total_pages} pages to scrape")
        
        # Process each page
        for page_num in range(1, total_pages + 1):
            print(f"Processing page {page_num} of {total_pages}")
            
            # For pages after first, navigate with Nao parameter
            if page_num > 1:
                nao_value = (page_num - 1) * 24
                page_url = f"https://www.target.com/s?searchTerm={search_term.replace(' ', '+')}&Nao={nao_value}"
                driver.get(page_url)
                time.sleep(2)
            
            # Scroll down to load content - more thorough scrolling
            scroll_positions = [0.25, 0.5, 0.75, 1.0]
            for position in scroll_positions:
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {position});")
                time.sleep(0.5)
            
            # Extract products from current page
            page_products = extract_products(driver)
            
            if page_products:
                # Process unique products
                new_products = 0
                for product in page_products:
                    if 'title' in product and product['title']:
                        product_key = product['title'].strip()
                        if product_key not in unique_products:
                            # Add store information
                            product['store'] = 'target'
                            unique_products[product_key] = product
                            all_products.append(product)
                            new_products += 1
                
                print(f"Extracted {len(page_products)} products from page {page_num}, {new_products} unique")
            else:
                print(f"No products found on page {page_num}, ending scrape")
                break
            
            # Save progress after each page
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_products, f, indent=2)
        
        print(f"Completed scraping. Total unique products: {len(all_products)}")
        
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        driver.quit()
    
    return all_products

def get_page_count(driver):
    """Get the total number of pages"""
    try:
        # Look for pagination information in page source
        html_source = driver.page_source
        
        # Method 1: Check JSON data
        total_pages_match = re.search(r'"totalPages":(\d+)', html_source)
        if total_pages_match:
            return int(total_pages_match.group(1))
        
        # Method 2: Check for "page X of Y" text
        page_text = driver.find_elements(By.XPATH, '//*[contains(text(), "page") and contains(text(), "of")]')
        for element in page_text:
            match = re.search(r'page\s+\d+\s+of\s+(\d+)', element.text.lower())
            if match:
                return int(match.group(1))
        
        # Method 3: Check for page number buttons
        page_buttons = driver.find_elements(By.CSS_SELECTOR, 'div[data-test="pagination"] button')
        max_page = 1
        
        for button in page_buttons:
            if button.text.strip().isdigit():
                max_page = max(max_page, int(button.text.strip()))
        
        if max_page > 1:
            return max_page
        
        return 1  # Default to 1 page
        
    except Exception as e:
        print(f"Error getting page count: {e}")
        return 1

def extract_products(driver):
    """Extract product data from the current page"""
    products = []
    
    try:
        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find product containers - try multiple selectors
        product_containers = soup.select('div[data-test="@web/site-top-of-funnel/ProductCardWrapper"]')
        
        # If that didn't work, try alternate selectors
        if not product_containers:
            product_containers = soup.select('div[data-test="product-card"]')
        if not product_containers:
            product_containers = soup.select('div[class*="ProductCard"]')
        if not product_containers:
            product_containers = soup.select('a[href*="/p/"]')  # Last resort, find product links
            
        print(f"Found {len(product_containers)} product containers")
        
        # Process each product
        for container in product_containers:
            product = {}
            
            # Extract title - try multiple methods
            # Method 1: Direct title elements
            title_elem = container.select_one('a[data-test="product-title"] span')
            if title_elem:
                product['title'] = title_elem.text.strip()
            
            # Method 2: Any element with truncate class
            if 'title' not in product or not product['title']:
                title_elem = container.select_one('.styles_ndsTruncate__GRSDE, [class*="Truncate"]')
                if title_elem:
                    product['title'] = title_elem.text.strip()
            
            # Method 3: Any heading element
            if 'title' not in product or not product['title']:
                title_elem = container.select_one('h2, h3, h4')
                if title_elem:
                    product['title'] = title_elem.text.strip()
                    
            # Method 4: Get from product link
            if 'title' not in product or not product['title']:
                link = container.select_one('a[href*="/p/"]')
                if link:
                    # Try text content of link
                    link_text = link.text.strip()
                    if link_text:
                        product['title'] = link_text
                    # Try alt text of image
                    else:
                        img = link.select_one('img')
                        if img and img.get('alt'):
                            product['title'] = img.get('alt').strip()
            
            # Extract price - try multiple methods
            price_elem = container.select_one('span[data-test="current-price"]')
            if price_elem:
                product['price'] = price_elem.text.strip()
            else:
                # Try any element with price in class
                price_elem = container.select_one('[class*="price"], [class*="Price"]')
                if price_elem:
                    price_text = price_elem.text.strip()
                    if '$' in price_text:
                        product['price'] = price_text
            
            # Extract URL and product ID
            link = container.select_one('a[href*="/p/"]')
            if link:
                href = link.get('href', '')
                product['url'] = 'https://www.target.com' + href if href.startswith('/') else href
                
                # Get product ID (TCIN)
                tcin_match = re.search(r'/A-(\d+)', href)
                if tcin_match:
                    product['tcin'] = tcin_match.group(1)
            
            # Extract image URL
            img = container.select_one('img')
            if img:
                product['image_url'] = img.get('src')
            
            # Extract brand if available
            brand_elem = container.select_one('[data-test*="brand"], [class*="brand"]')
            if brand_elem:
                product['brand'] = brand_elem.text.strip()
            
            # Only add products with a title
            if 'title' in product and product['title']:
                products.append(product)
    
    except Exception as e:
        print(f"Error extracting products: {e}")
    
    return products

if __name__ == "__main__":
    search_term = input("Enter search term (e.g., 'primer', 'foundation'): ")
    products = scrape_target_products(search_term)
    print(f"Scraped {len(products)} Target products for '{search_term}'")
