import os
import json
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import matplotlib.ticker as mtick

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

def create_improved_boxplots(df, output_dir="visualizations"):
    """Create improved box plots with better formatting and outlier handling"""
    if df.empty:
        print("No data available for plotting box plots.")
        return
        
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Boxplot by Store
    plt.figure(figsize=(12, 8))
    
    # Create box plot with better handling of outliers
    ax = sns.boxplot(
        x='store', 
        y='price', 
        data=df,
        showfliers=True,  # Show outliers
        fliersize=3        # Make outliers smaller
    )
    
    # Customize plot
    plt.title('Price Distribution by Store', fontsize=16)
    plt.xlabel('Store', fontsize=14)
    plt.ylabel('Price ($)', fontsize=14)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Format y-axis as currency
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:.2f}'))
    
    # Add median values as text
    medians = df.groupby('store')['price'].median()
    for i, store in enumerate(medians.index):
        plt.text(i, medians[store] + 0.5, f'${medians[store]:.2f}', 
                 ha='center', va='bottom', fontsize=11, color='black')
    
    # Add count and price range information
    stats = df.groupby('store')['price'].agg(['count', 'min', 'max'])
    store_names = ['Target', 'RiteAid', 'Ulta']
    for i, store in enumerate(stats.index):
        plt.text(
            i, 
            -5,  # Position below the x-axis
            f"n={stats.loc[store, 'count']}\nRange: ${stats.loc[store, 'min']:.2f}-${stats.loc[store, 'max']:.2f}",
            ha='center', 
            va='top',
            fontsize=9
        )
    
    plt.tight_layout()
    
    # Save figure
    plt.savefig(os.path.join(output_dir, 'improved_store_boxplots.png'), dpi=300)
    plt.close()
    
    # 2. Boxplot by Category
    plt.figure(figsize=(14, 8))
    
    # Create box plot
    ax = sns.boxplot(
        x='category', 
        y='price', 
        data=df,
        showfliers=True,
        fliersize=3
    )
    
    # Customize plot
    plt.title('Price Distribution by Product Category', fontsize=16)
    plt.xlabel('Product Category', fontsize=14)
    plt.ylabel('Price ($)', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Format y-axis as currency
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:.2f}'))
    
    # Add median values as text
    medians = df.groupby('category')['price'].median()
    for i, category in enumerate(medians.index):
        plt.text(i, medians[category] + 0.5, f'${medians[category]:.2f}', 
                 ha='center', va='bottom', fontsize=11, color='black')
    
    # Add count and price range information
    stats = df.groupby('category')['price'].agg(['count', 'min', 'max'])
    for i, category in enumerate(stats.index):
        plt.text(
            i, 
            -5,  # Position below the x-axis
            f"n={stats.loc[category, 'count']}\nRange: ${stats.loc[category, 'min']:.2f}-${stats.loc[category, 'max']:.2f}",
            ha='center', 
            va='top',
            fontsize=9
        )
    
    plt.tight_layout()
    
    # Save figure
    plt.savefig(os.path.join(output_dir, 'improved_category_boxplots.png'), dpi=300)
    plt.close()
    
    # 3. Combined boxplot by category and store
    plt.figure(figsize=(16, 10))
    
    # Create box plot
    ax = sns.boxplot(
        x='category', 
        y='price', 
        hue='store', 
        data=df,
        showfliers=True,
        fliersize=2
    )
    
    # Customize plot
    plt.title('Price Distribution by Category and Store', fontsize=16)
    plt.xlabel('Product Category', fontsize=14)
    plt.ylabel('Price ($)', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Format y-axis as currency
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:.2f}'))
    
    plt.legend(title='Store', loc='upper right')
    plt.tight_layout()
    
    # Save figure
    plt.savefig(os.path.join(output_dir, 'improved_combined_boxplots.png'), dpi=300)
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
    
    # Create improved boxplots
    create_improved_boxplots(df, output_dir)
    
    print(f"Improved boxplot visualizations created in '{output_dir}' directory.")

if __name__ == "__main__":
    main()
