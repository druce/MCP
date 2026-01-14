#!/opt/anaconda3/envs/mcpskills/bin/python3
"""
Fidelity Portfolio Aggregation Skill

Reads CSV files from the import directory and creates an aggregated positions file
with archival copy.

Usage:
    python aggregate_positions.py [--import-dir DIR]

Output files:
    - aggregate_positions.csv (current aggregated positions)
    - aggregate_positions_YYYYMMDD.csv (dated archive)
"""

import pandas as pd
import glob
import os
import re
from datetime import datetime
import argparse
import sys


def clean_currency_value(value):
    """Remove $, %, and commas from currency values and convert to float."""
    if pd.isna(value):
        return None
    value_str = str(value)
    # Remove $, %, commas
    cleaned = re.sub(r'[$,%]', '', value_str)
    # Handle empty strings or '--'
    if cleaned == '' or cleaned == '--':
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def aggregate_positions(import_dir):
    """
    Aggregate portfolio positions from CSV files in import directory.

    Args:
        import_dir (str): Path to directory containing Fidelity CSV exports

    Returns:
        pd.DataFrame: Aggregated positions data
    """
    print(f"Reading CSV files from: {import_dir}")

    # Find all CSV files
    csv_pattern = os.path.join(import_dir, "*.csv")
    all_files = glob.glob(csv_pattern)

    if not all_files:
        print(f"ERROR: No CSV files found in {import_dir}")
        return None

    print(f"Found {len(all_files)} CSV file(s)")

    # Read and combine all CSV files
    df_list = []
    for filename in all_files:
        try:
            df = pd.read_csv(filename, encoding='utf-8-sig', index_col=False)  # utf-8-sig handles BOM, don't use index
            df_list.append(df)
            print(f"  - Loaded: {os.path.basename(filename)} ({len(df)} rows)")
        except Exception as e:
            print(f"  - ERROR loading {filename}: {e}")
            continue

    if not df_list:
        print("ERROR: No CSV files could be loaded successfully")
        return None

    # Concatenate all dataframes
    combined_df = pd.concat(df_list, ignore_index=True)
    print(f"\nCombined data: {len(combined_df)} total rows")

    # Clean numeric columns
    numeric_cols = ['Last Price', 'Current Value', 'Cost Basis Total',
                   'Average Cost Basis', 'Quantity']

    for col in numeric_cols:
        if col in combined_df.columns:
            combined_df[col] = combined_df[col].apply(clean_currency_value)

    # Normalize cash symbols
    # FDRXX** (money market) → Cash
    # Pending Activity → Cash
    combined_df.loc[combined_df['Symbol'] == 'FDRXX**', 'Symbol'] = 'Cash'
    combined_df.loc[combined_df['Symbol'] == 'Pending activity', 'Symbol'] = 'Cash'
    combined_df.loc[combined_df['Symbol'] == 'Pending Activity', 'Symbol'] = 'Cash'

    # Set description for cash
    cash_mask = combined_df['Symbol'] == 'Cash'
    if cash_mask.any():
        combined_df.loc[cash_mask, 'Description'] = 'Cash'
        # For cash, set quantity = current value
        combined_df.loc[cash_mask, 'Quantity'] = combined_df.loc[cash_mask, 'Current Value']

    # Drop rows without current value
    combined_df = combined_df.dropna(subset=['Current Value'])

    # Group by Symbol and aggregate
    # For Type, we'll take the first non-null value
    agg_dict = {
        'Description': 'first',
        'Quantity': 'sum',
        'Last Price': 'first',  # Price should be same across accounts
        'Current Value': 'sum',
        'Cost Basis Total': 'sum',
        'Type': 'first'
    }

    aggregated = combined_df.groupby('Symbol').agg(agg_dict).reset_index()

    # Calculate average cost basis from totals
    # average_cost_basis = total_cost_basis / quantity (except for cash)
    aggregated['Average Cost Basis'] = aggregated.apply(
        lambda row: row['Cost Basis Total'] / row['Quantity']
        if row['Quantity'] != 0 and pd.notna(row['Cost Basis Total']) and row['Symbol'] != 'Cash'
        else None,
        axis=1
    )

    # Rename columns to match desired output format
    output_df = aggregated.rename(columns={
        'Symbol': 'symbol',
        'Description': 'description',
        'Quantity': 'quantity',
        'Last Price': 'last_price',
        'Current Value': 'value',
        'Average Cost Basis': 'average_cost_basis',
        'Cost Basis Total': 'total_cost_basis',
        'Type': 'type'
    })

    # Reorder columns
    column_order = ['symbol', 'description', 'quantity', 'last_price', 'value',
                   'average_cost_basis', 'total_cost_basis', 'type']
    output_df = output_df[column_order]

    # Sort by value descending
    output_df = output_df.sort_values('value', ascending=False)

    print(f"\nAggregated to {len(output_df)} unique positions")
    print(f"Total portfolio value: ${output_df['value'].sum():,.2f}")

    return output_df


def save_outputs(df, base_dir):
    """
    Save aggregated positions to both current and dated archive files.

    Args:
        df (pd.DataFrame): Aggregated positions data
        base_dir (str): Base directory for output files
    """
    if df is None or len(df) == 0:
        print("ERROR: No data to save")
        return False

    # Create output directory if it doesn't exist
    os.makedirs(base_dir, exist_ok=True)

    # Current date in YYYYMMDD format
    date_str = datetime.now().strftime('%Y%m%d')

    # Output file paths
    current_file = os.path.join(base_dir, 'aggregate_positions.csv')
    archive_file = os.path.join(base_dir, f'aggregate_positions_{date_str}.csv')

    try:
        # Save current file
        df.to_csv(current_file, index=False, float_format='%.2f')
        print(f"\n✓ Saved current positions to: {current_file}")

        # Save archive file
        df.to_csv(archive_file, index=False, float_format='%.2f')
        print(f"✓ Saved archive to: {archive_file}")

        return True

    except Exception as e:
        print(f"\nERROR saving output files: {e}")
        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Aggregate Fidelity portfolio positions from CSV exports'
    )
    parser.add_argument(
        '--import-dir',
        default='import',
        help='Directory containing CSV exports (default: ./import)'
    )
    parser.add_argument(
        '--output-dir',
        default='data',
        help='Directory for output files (default: ./data)'
    )

    args = parser.parse_args()

    # Resolve paths
    import_dir = os.path.abspath(args.import_dir)
    output_dir = os.path.abspath(args.output_dir)

    # Check if import directory exists
    if not os.path.isdir(import_dir):
        print(f"ERROR: Import directory not found: {import_dir}")
        print(f"\nPlease specify the correct directory with --import-dir")
        return 1

    print("=" * 60)
    print("Fidelity Portfolio Aggregation")
    print("=" * 60)

    # Aggregate positions
    aggregated_df = aggregate_positions(import_dir)

    if aggregated_df is None:
        return 1

    # Display summary
    print("\n" + "=" * 60)
    print("AGGREGATED POSITIONS SUMMARY")
    print("=" * 60)
    print(aggregated_df.to_string(index=False))

    # Save output files
    if save_outputs(aggregated_df, output_dir):
        print("\n" + "=" * 60)
        print("SUCCESS: Aggregation complete!")
        print("=" * 60)
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
