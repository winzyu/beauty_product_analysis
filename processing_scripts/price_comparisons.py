import os
import json
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import matplotlib.ticker as mtick
import textwrap

# Set style for plots
plt.style.use('ggplot')
sns.set_palette("pastel")

def load_data(base_dir="sorted_data"):
    """Load all data from sorted_data directory into a pandas DataFrame"""
    stores = ["target", "riteaid", "ulta"]
    categories = [
        "blush", "concealer", "eyebrow_gel", "foundation", 
        "lip_gloss", "powder", "primer", "setting_spray"
    ]
    
    all_products = []
    
    print("Loading makeup data...")
    for store in stores:
        for category in categories:
            category_dir = os.path.join(base_dir, store, category)
            if not os.path.exists(category_dir):
                continue
                
            # Find all JSON files in this directory
            json_files = glob.glob(os.path.join(category_dir, "*.json"))
            
            if not json_files:
                continue
                
            # Process the first JSON file found
            file_path = json_files[0]
            try:
                with open(file_path, 'r') as f:
                    products = json.load(f)
                    if products and isinstance(products, list):
                        # Add category to each product if not already present
                        for product in products:
                            if 'category' not in product:
                                product['category'] = category
                        
                        all_products.extend(products)
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
    
    # Convert to DataFrame
    df = pd.DataFrame(all_products)
    
    if df.empty:
        print("No products were loaded. Check your data directories.")
        return pd.DataFrame()
        
    # Make sure 'price' column is numeric
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    return df

def get_cheapest_products(df):
    """Get the cheapest product in each category for each store"""
    if df.empty:
        return pd.DataFrame()
        
    # Group by store and category, find minimum price
    cheapest = df.loc[df.groupby(['store', 'category'])['price'].idxmin()]
    return cheapest

def plot_cheapest_by_category(df, output_dir="visualizations"):
    """Create improved bar chart comparing cheapest products for each category across stores"""
    if df.empty:
        print("No data available for plotting cheapest by category.")
        return
        
    os.makedirs(output_dir, exist_ok=True)
    
    # Get cheapest products
    cheapest = get_cheapest_products(df)
    
    # Create figure
    plt.figure(figsize=(16, 10))
    
    # Plot using seaborn for better categorical visualization
    ax = sns.barplot(x='category', y='price', hue='store', data=cheapest)
    
    # Add product names as text above bars with better formatting
    for i, row in cheapest.iterrows():
        # Get x-coordinate for this bar
        category_index = list(cheapest['category'].unique()).index(row['category'])
        store_index = list(cheapest['store'].unique()).index(row['store'])
        
        # Calculate the x position for this specific bar
        # This depends on how seaborn positions the bars in grouped bar charts
        width = 0.8 / len(cheapest['store'].unique())
        x_pos = category_index + (store_index - 1) * width + width/2
        
        # Truncate and wrap product name
        name = row['name']
        if len(name) > 20:
            name = name[:18] + '...'
        
        # Add text with smaller font and vertical orientation
        ax.text(
            x=x_pos,
            y=row['price'] + 0.1,
            s=name,
            ha='center',
            va='bottom',
            color='black',
            rotation=90,
            fontsize=8
        )
    
    # Customize plot
    plt.title('Cheapest Makeup Products by Category and Store', fontsize=16)
    plt.xlabel('Product Category', fontsize=14)
    plt.ylabel('Price ($)', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Format y-axis as currency
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:.2f}'))
    
    plt.legend(title='Store', loc='upper right')
    plt.tight_layout()
    
    # Save figure
    plt.savefig(os.path.join(output_dir, 'improved_cheapest_by_category.png'), dpi=300)
    plt.close()

def plot_cheapest_vs_median(df, output_dir="visualizations"):
    """Create comparison of cheapest vs. median prices for each store"""
    if df.empty:
        print("No data available for plotting cheapest vs. median.")
        return
        
    os.makedirs(output_dir, exist_ok=True)
    
    # Calculate median prices by store and category
    median_prices = df.groupby(['store', 'category'])['price'].median().reset_index()
    median_prices['price_type'] = 'Median'
    
    # Get cheapest prices
    cheapest = get_cheapest_products(df)
    cheapest = cheapest[['store', 'category', 'price']].copy()
    cheapest['price_type'] = 'Cheapest'
    
    # Combine datasets
    combined = pd.concat([median_prices, cheapest])
    
    # Create grouped bar charts for each store
    stores = df['store'].unique()
    
    # Create 3 subplots (one for each store)
    fig, axes = plt.subplots(len(stores), 1, figsize=(14, len(stores) * 4), sharex=True)
    
    # Format y-axis as currency for all subplots
    for ax in axes:
        ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:.2f}'))
    
    # Plot data for each store
    for i, store in enumerate(stores):
        # Filter data for this store
        store_data = combined[combined['store'] == store]
        
        # Plot on the corresponding subplot
        sns.barplot(
            x='category', 
            y='price', 
            hue='price_type', 
            data=store_data,
            ax=axes[i],
            palette=['skyblue', 'coral']
        )
        
        # Customize subplot
        axes[i].set_title(f'{store.capitalize()} - Cheapest vs. Median Prices', fontsize=14)
        axes[i].set_ylabel('Price ($)', fontsize=12)
        axes[i].grid(axis='y', linestyle='--', alpha=0.7)
        
        # Add value labels
        for j, bar in enumerate(axes[i].patches):
            axes[i].text(
                bar.get_x() + bar.get_width()/2., 
                bar.get_height() + 0.1, 
                f'${bar.get_height():.2f}', 
                ha='center',
                fontsize=8
            )
        
        # Clean up legend and labels
        if i < len(stores) - 1:
            axes[i].set_xlabel('')
        else:
            axes[i].set_xlabel('Product Category', fontsize=12)
        
        # Set consistent legend
        axes[i].legend(title='Price Type')
    
    # Rotate x-axis labels on the bottom subplot
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    
    # Save figure
    plt.savefig(os.path.join(output_dir, 'cheapest_vs_median.png'), dpi=300)
    plt.close()

def create_category_cheapest_prices(df, output_dir="visualizations"):
    """Create visualization comparing cheapest prices across categories between stores"""
    if df.empty:
        return
        
    # Get cheapest product in each category for each store
    cheapest = get_cheapest_products(df)
    
    # Create bar chart
    plt.figure(figsize=(14, 8))
    
    # Plot using seaborn for better categorical visualization
    ax = sns.barplot(x='category', y='price', hue='store', data=cheapest)
    
    # Customize plot
    plt.title('Cheapest Product Prices by Category and Store', fontsize=16)
    plt.xlabel('Product Category', fontsize=14)
    plt.ylabel('Price ($)', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add value labels
    for i, bar in enumerate(ax.patches):
        ax.text(
            bar.get_x() + bar.get_width()/2., 
            bar.get_height() + 0.1, 
            f'${bar.get_height():.2f}', 
            ha='center',
            fontsize=9
        )
    
    # Format y-axis as currency
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:.2f}'))
    
    plt.legend(title='Store', loc='upper right')
    plt.tight_layout()
    
    # Save figure
    plt.savefig(os.path.join(output_dir, 'category_cheapest_comparison.png'), dpi=300)
    plt.close()

def main():
    # Create output directory
    output_dir = "visualizations"
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    df = load_data()
    
    if df.empty:
        print("No data found. Please check the data directory.")
        return
    
    # Create improved bar plots
    plot_cheapest_by_category(df, output_dir)
    
    # Create comparison of cheapest vs. median prices
    plot_cheapest_vs_median(df, output_dir)
    
    # Create category cheapest price comparison
    create_category_cheapest_prices(df, output_dir)
    
    print(f"Improved bar plot visualizations created in '{output_dir}' directory.")

if __name__ == "__main__":
    main()
