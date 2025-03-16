import os
import json
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import matplotlib.ticker as mtick
from matplotlib.gridspec import GridSpec

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

def get_cheapest_overall(df):
    """Get the cheapest product in each category across all stores"""
    if df.empty:
        return pd.DataFrame()
        
    # Group by category, find minimum price
    cheapest_overall = df.loc[df.groupby('category')['price'].idxmin()]
    return cheapest_overall

def create_improved_stacked_bar(df, output_dir="visualizations"):
    """Create improved stacked bar chart for routine comparison"""
    if df.empty:
        print("No data available for creating routine breakdown.")
        return
        
    os.makedirs(output_dir, exist_ok=True)
    
    # Get cheapest products for each store
    cheapest_by_store = get_cheapest_products(df)
    
    # Get cheapest overall products across stores
    cheapest_overall = get_cheapest_overall(df)
    
    # Create routine breakdown dataframes
    routine_data = []
    
    # For each store routine
    for store in ['target', 'riteaid', 'ulta']:
        store_products = cheapest_by_store[cheapest_by_store['store'] == store]
        for _, product in store_products.iterrows():
            routine_data.append({
                'store': store,
                'strategy': f"{store} routine",
                'category': product['category'],
                'product_name': product['name'],
                'price': product['price']
            })
    
    # For optimal multi-store routine
    for _, product in cheapest_overall.iterrows():
        routine_data.append({
            'store': product['store'],
            'strategy': 'optimal routine',
            'category': product['category'],
            'product_name': product['name'],
            'price': product['price']
        })
    
    # Convert to DataFrame
    routine_df = pd.DataFrame(routine_data)
    
    # Create stacked bar chart for routine breakdown
    plt.figure(figsize=(16, 8))
    
    # Calculate total costs for each strategy
    strategy_totals = routine_df.groupby('strategy')['price'].sum().to_dict()
    
    # Create pivot table for stacked bar chart
    pivot_data = routine_df.pivot_table(
        index='strategy', 
        columns='category', 
        values='price', 
        aggfunc='sum'
    )
    
    # Apply custom order to strategies
    ordered_strategies = ['target routine', 'riteaid routine', 'ulta routine', 'optimal routine']
    pivot_data = pivot_data.reindex(ordered_strategies)
    
    # Get category order by average price (highest first)
    category_order = pivot_data.mean().sort_values(ascending=False).index.tolist()
    pivot_data = pivot_data[category_order]
    
    # Plot stacked bar chart
    ax = pivot_data.plot(kind='bar', stacked=True, figsize=(16, 8))
    
    # Customize plot
    plt.title('Makeup Routine Cost Breakdown by Shopping Strategy', fontsize=18)
    plt.xlabel('Shopping Strategy', fontsize=14)
    plt.ylabel('Total Cost ($)', fontsize=14)
    plt.xticks(rotation=0)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add total cost annotations on top of bars
    for i, strategy in enumerate(pivot_data.index):
        total = strategy_totals[strategy]
        plt.text(i, total + 0.3, f'${total:.2f}', ha='center', fontsize=12, fontweight='bold')
    
    # Format y-axis as currency
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:.2f}'))
    
    # Adjust legend
    plt.legend(title='Product Category', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    
    # Save figure
    plt.savefig(os.path.join(output_dir, 'improved_routine_breakdown.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    return routine_df

def create_improved_savings_analysis(routine_df, output_dir="visualizations"):
    """Create improved analysis of potential savings between different shopping strategies"""
    if routine_df.empty:
        return
        
    # Calculate total costs for each strategy
    strategy_totals = routine_df.groupby('strategy')['price'].sum().reset_index()
    
    # Get optimal routine cost
    optimal_rows = strategy_totals[strategy_totals['strategy'] == 'optimal routine']
    if optimal_rows.empty:
        print("Warning: No optimal routine found in data")
        return strategy_totals
        
    optimal_cost = optimal_rows['price'].values[0]
    
    # Calculate savings compared to optimal
    strategy_totals['savings_vs_optimal'] = strategy_totals['price'] - optimal_cost
    strategy_totals['savings_percentage'] = (strategy_totals['savings_vs_optimal'] / strategy_totals['price']) * 100
    
    # Create color mapping for strategies
    color_map = {
        'target routine': 'salmon',
        'riteaid routine': 'skyblue',
        'ulta routine': 'lightgreen',
        'optimal routine': 'gold'
    }
    
    # FIGURE 1: Side-by-side comparison of total costs and savings
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(1, 2, width_ratios=[1, 1], figure=fig)
    
    # Plot 1: Total costs by strategy (including optimal)
    ax1 = fig.add_subplot(gs[0, 0])
    bars1 = ax1.bar(
        strategy_totals['strategy'], 
        strategy_totals['price'],
        color=[color_map[s] for s in strategy_totals['strategy']]
    )
    
    # Add value labels on top of bars
    for bar in bars1:
        height = bar.get_height()
        ax1.text(
            bar.get_x() + bar.get_width()/2., 
            height + 0.3, 
            f'${height:.2f}', 
            ha='center', 
            va='bottom',
            fontsize=12,
            fontweight='bold'
        )
    
    # Customize plot
    ax1.set_title('Total Makeup Routine Cost by Shopping Strategy', fontsize=16)
    ax1.set_xlabel('Shopping Strategy', fontsize=14)
    ax1.set_ylabel('Total Cost ($)', fontsize=14)
    ax1.tick_params(axis='x', rotation=0)
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    ax1.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:.2f}'))
    
    # Plot 2: Savings comparison (excluding optimal)
    ax2 = fig.add_subplot(gs[0, 1])
    comparison_data = strategy_totals[strategy_totals['strategy'] != 'optimal routine']
    
    # Sort by savings amount (largest first)
    comparison_data = comparison_data.sort_values('savings_vs_optimal', ascending=False)
    
    bars2 = ax2.bar(
        comparison_data['strategy'], 
        comparison_data['savings_vs_optimal'],
        color=[color_map[s] for s in comparison_data['strategy']]
    )
    
    # Add value labels with both dollar and percentage
    for bar in bars2:
        height = bar.get_height()
        strategy = bar.get_x() + bar.get_width()/2.
        idx = comparison_data[comparison_data['strategy'] == ax2.get_xticklabels()[int(strategy)].get_text()].index[0]
        percentage = comparison_data.loc[idx, 'savings_percentage']
        
        ax2.text(
            strategy, 
            height + 0.1, 
            f'${height:.2f} ({percentage:.1f}%)', 
            ha='center', 
            va='bottom',
            fontsize=10,
            fontweight='bold'
        )
    
    # Customize plot
    ax2.set_title('Potential Savings vs. Optimal Multi-store Strategy', fontsize=16)
    ax2.set_xlabel('Shopping Strategy', fontsize=14)
    ax2.set_ylabel('Extra Cost Above Optimal ($)', fontsize=14)
    ax2.tick_params(axis='x', rotation=0)
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    ax2.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:.2f}'))
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'improved_savings_comparison.png'), dpi=300)
    plt.close()
    
    # FIGURE 2: Detailed savings breakdown with category-level information
    plt.figure(figsize=(16, 10))
    
    # Create a dataframe for category-level savings
    category_savings = []
    
    # Calculate savings by category for each store strategy
    categories = routine_df['category'].unique()
    
    # Get optimal routine data by category
    optimal_by_category = routine_df[routine_df['strategy'] == 'optimal routine'].set_index('category')['price'].to_dict()
    
    # Calculate savings for each store and category
    for strategy in ['target routine', 'riteaid routine', 'ulta routine']:
        strategy_df = routine_df[routine_df['strategy'] == strategy]
        
        for _, row in strategy_df.iterrows():
            category = row['category']
            store_price = row['price']
            optimal_price = optimal_by_category.get(category, 0)
            savings = store_price - optimal_price
            
            if savings > 0:  # Only add if there are actual savings
                category_savings.append({
                    'strategy': strategy,
                    'category': category,
                    'savings': savings
                })
    
    # Convert to DataFrame and pivot
    if category_savings:
        savings_df = pd.DataFrame(category_savings)
        pivot_savings = savings_df.pivot_table(
            index='strategy', 
            columns='category', 
            values='savings', 
            aggfunc='sum'
        ).fillna(0)
        
        # Sort categories by total savings
        category_order = savings_df.groupby('category')['savings'].sum().sort_values(ascending=False).index
        pivot_savings = pivot_savings[category_order]
        
        # Plot stacked bar chart
        ax = pivot_savings.plot(kind='bar', stacked=True, figsize=(16, 10))
        
        # Customize plot
        plt.title('Savings Breakdown by Category vs. Optimal Strategy', fontsize=18)
        plt.xlabel('Shopping Strategy', fontsize=14)
        plt.ylabel('Potential Savings ($)', fontsize=14)
        plt.xticks(rotation=0)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Add total annotations on top of bars
        for i, strategy in enumerate(pivot_savings.index):
            total = pivot_savings.loc[strategy].sum()
            plt.text(i, total + 0.1, f'${total:.2f}', ha='center', fontsize=12, fontweight='bold')
        
        # Format y-axis as currency
        ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:.2f}'))
        
        # Adjust legend
        plt.legend(title='Product Category', bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        
        # Save figure
        plt.savefig(os.path.join(output_dir, 'savings_by_category.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    # Create text summary of savings
    with open(os.path.join(output_dir, 'improved_savings_summary.txt'), 'w') as f:
        f.write("===== MAKEUP ROUTINE SAVINGS ANALYSIS =====\n\n")
        
        f.write("Total Routine Costs:\n")
        for _, row in strategy_totals.iterrows():
            f.write(f"  {row['strategy'].title()}: ${row['price']:.2f}\n")
        f.write("\n")
        
        f.write("Potential Savings with Optimal Multi-store Strategy:\n")
        for _, row in comparison_data.iterrows():
            f.write(f"  vs. {row['strategy'].title()}: ${row['savings_vs_optimal']:.2f} " +
                  f"({row['savings_percentage']:.1f}% of total cost)\n")
        
        f.write("\nBreakdown of Savings by Category:\n")
        if category_savings:
            for strategy in ['target routine', 'riteaid routine', 'ulta routine']:
                f.write(f"\n{strategy.title()}:\n")
                strategy_savings = savings_df[savings_df['strategy'] == strategy]
                for _, row in strategy_savings.iterrows():
                    f.write(f"  {row['category'].title()}: ${row['savings']:.2f}\n")
    
    return strategy_totals

def create_routine_product_tables(routine_df, output_dir="visualizations"):
    """Create simplified tables showing products in each routine"""
    if routine_df.empty:
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each strategy
    strategies = ['target routine', 'riteaid routine', 'ulta routine', 'optimal routine']
    
    for strategy in strategies:
        strategy_data = routine_df[routine_df['strategy'] == strategy]
        if strategy_data.empty:
            continue
            
        # Sort by category for consistent display
        strategy_data = strategy_data.sort_values('category')
        
        # Calculate total
        total = strategy_data['price'].sum()
        
        # Create a DataFrame for output
        output_data = []
        for _, row in strategy_data.iterrows():
            output_data.append({
                'Category': row['category'].replace('_', ' ').title(),
                'Product': row['product_name'],
                'Store': row['store'].title(),
                'Price': f"${row['price']:.2f}"
            })
            
        # Add total row
        output_data.append({
            'Category': 'TOTAL',
            'Product': '',
            'Store': '',
            'Price': f"${total:.2f}"
        })
        
        # Convert to DataFrame
        output_df = pd.DataFrame(output_data)
        
        # Save as CSV
        csv_path = os.path.join(output_dir, f"{strategy.replace(' ', '_')}_products.csv")
        output_df.to_csv(csv_path, index=False)
        
        # Save as text file
        txt_path = os.path.join(output_dir, f"{strategy.replace(' ', '_')}_products.txt")
        with open(txt_path, 'w') as f:
            f.write(f"{strategy.title()} (Total: ${total:.2f})\n\n")
            f.write(output_df.to_string(index=False))
        
        print(f"  - Created table for {strategy}")

def main():
    """Run the makeup routine analysis"""
    # Create output directory
    output_dir = "visualizations"
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    print("Loading makeup data...")
    df = load_data()
    
    if df.empty:
        print("No data found. Please check the data directory.")
        return
    
    print(f"Loaded {len(df)} products across {df['store'].nunique()} stores.")
    
    # Create improved stacked bar chart for routine costs
    print("Creating routine breakdown visualization...")
    routine_df = create_improved_stacked_bar(df, output_dir)
    
    # Create improved savings analysis
    print("Creating savings analysis visualizations...")
    create_improved_savings_analysis(routine_df, output_dir)
    
    # Create simplified product tables for each routine
    print("Creating product tables for each routine...")
    create_routine_product_tables(routine_df, output_dir)
    
    print(f"All routine analysis visualizations created in '{output_dir}' directory.")

if __name__ == "__main__":
    main()
