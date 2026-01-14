#!/opt/anaconda3/envs/mcpskills/bin/python3
"""
Fidelity Portfolio Visualization Skill

Creates interactive HTML sunburst chart showing portfolio allocation by category hierarchy.
Supports drill-down navigation through L1 -> L2 -> L3 -> L4 -> Symbol levels.

Usage:
    ./visualize_allocation.py [--data-dir DIR] [--output-dir DIR]

Output:
    - Interactive HTML sunburst chart in dataviz/ directory
    - Displays allocation percentages and values
    - Hover shows detailed position information
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
import argparse
from datetime import datetime


def load_data(data_dir):
    """
    Load aggregate positions and security mapping.

    Args:
        data_dir (str): Directory containing CSV files

    Returns:
        tuple: (positions_df, mapping_df) or (None, None) on error
    """
    positions_file = os.path.join(data_dir, 'aggregate_positions.csv')
    mapping_file = os.path.join(data_dir, 'security_mapping.csv')

    print(f"Loading data from: {data_dir}")

    # Check if files exist
    if not os.path.exists(positions_file):
        print(f"ERROR: Positions file not found: {positions_file}")
        return None, None

    if not os.path.exists(mapping_file):
        print(f"ERROR: Mapping file not found: {mapping_file}")
        return None, None

    try:
        positions_df = pd.read_csv(positions_file)
        print(f"  ✓ Loaded {len(positions_df)} positions")

        mapping_df = pd.read_csv(mapping_file)
        print(f"  ✓ Loaded {len(mapping_df)} security mappings")

        return positions_df, mapping_df

    except Exception as e:
        print(f"ERROR loading data: {e}")
        return None, None


def merge_and_prepare_data(positions_df, mapping_df):
    """
    Merge positions with category mappings and prepare for visualization.

    Args:
        positions_df (pd.DataFrame): Aggregate positions
        mapping_df (pd.DataFrame): Security category mappings

    Returns:
        pd.DataFrame: Merged and prepared data
    """
    # Merge positions with mappings
    merged = positions_df.merge(mapping_df, left_on='symbol', right_on='Symbol', how='left')

    # Check for unmapped securities
    unmapped = merged[merged['L1'].isna()]
    if len(unmapped) > 0:
        print(f"\nWARNING: {len(unmapped)} unmapped securities:")
        for symbol in unmapped['symbol']:
            print(f"  - {symbol}")

    # Remove unmapped securities for visualization
    merged = merged[merged['L1'].notna()].copy()

    # Fill empty category levels with empty string
    for col in ['L2', 'L3', 'L4']:
        merged[col] = merged[col].fillna('')

    # Calculate total portfolio value (handling negative positions)
    total_value = merged['value'].sum()

    print(f"\n✓ Prepared {len(merged)} securities for visualization")
    print(f"  Total portfolio value: ${total_value:,.2f}")

    return merged


def create_sunburst_data(df):
    """
    Create hierarchical data structure for sunburst chart.

    Args:
        df (pd.DataFrame): Merged position and category data

    Returns:
        pd.DataFrame: Formatted for plotly sunburst
    """
    # Build hierarchy: Root -> L1 -> L2 -> L3 -> L4 -> Symbol
    rows = []

    # Add each position at the leaf level (Symbol)
    for _, row in df.iterrows():
        # Build the path: L1 / L2 / L3 / L4 / Symbol
        path_parts = [row['L1']]

        if row['L2']:
            path_parts.append(row['L2'])
        if row['L3']:
            path_parts.append(row['L3'])
        if row['L4']:
            path_parts.append(row['L4'])

        path_parts.append(row['symbol'])

        # Build parent path (everything except the last element)
        parent = path_parts[-2] if len(path_parts) > 1 else ''

        rows.append({
            'label': row['symbol'],
            'parent': parent,
            'value': abs(row['value']),  # Use absolute value for sizing
            'actual_value': row['value'],  # Keep actual (possibly negative) value
            'quantity': row['quantity'],
            'last_price': row['last_price'],
            'description': row['description'],
            'type': row['type'],
            'path': ' > '.join(path_parts),
            'L1_category': row['L1']  # Track L1 category for coloring
        })

    # Add intermediate nodes (L4, L3, L2, L1)
    # We need to aggregate values at each level

    # Group by each level and sum values
    for level_num, level_col in enumerate(['L4', 'L3', 'L2', 'L1'], start=1):
        if level_col in df.columns:
            grouped = df[df[level_col] != ''].groupby(
                [col for col in ['L1', 'L2', 'L3', 'L4'][:5-level_num] if col in df.columns]
            ).agg({
                'value': 'sum'
            }).reset_index()

            for _, row in grouped.iterrows():
                current_level = row[level_col]
                if not current_level:
                    continue

                # Determine parent
                if level_col == 'L1':
                    parent = ''
                elif level_col == 'L2':
                    parent = row['L1']
                elif level_col == 'L3':
                    parent = row['L2']
                elif level_col == 'L4':
                    parent = row['L3']

                # Check if this node already exists
                existing = [r for r in rows if r['label'] == current_level and r['parent'] == parent]
                if not existing:
                    rows.append({
                        'label': current_level,
                        'parent': parent,
                        'value': abs(row['value']),
                        'actual_value': row['value'],
                        'quantity': None,
                        'last_price': None,
                        'description': None,
                        'type': None,
                        'path': None,
                        'L1_category': row['L1']  # Track L1 category for coloring
                    })

    return pd.DataFrame(rows)


def create_sunburst_chart(df, output_path):
    """
    Create interactive sunburst chart using plotly.

    Args:
        df (pd.DataFrame): Hierarchical data for sunburst
        output_path (str): Path to save HTML file

    Returns:
        bool: True if successful
    """
    try:
        # Define Set1 color palette for L1 categories
        color_map = {
            'CASH': '#4DAF4A',      # Green (Set1)
            'GROWTH': '#377EB8',    # Blue (Set1)
            'DEFLATION': '#E41A1C', # Red (Set1)
            'INFLATION': '#FF7F00'  # Orange (Set1)
        }

        # Create custom hover text
        df['hover_text'] = df.apply(lambda row:
            f"<b>{row['label']}</b><br>" +
            f"Value: ${row['actual_value']:,.2f}<br>" +
            (f"Quantity: {row['quantity']:,.2f}<br>" if pd.notna(row['quantity']) else "") +
            (f"Price: ${row['last_price']:,.2f}<br>" if pd.notna(row['last_price']) else "") +
            (f"Type: {row['type']}<br>" if pd.notna(row['type']) else "") +
            (f"Description: {row['description']}" if pd.notna(row['description']) else ""),
            axis=1
        )

        # Create sunburst chart with Set1 color palette
        fig = px.sunburst(
            df,
            names='label',
            parents='parent',
            values='value',
            color='L1_category',
            color_discrete_map=color_map,
            hover_data={'hover_text': True},
            title=f"Portfolio Allocation by Category - {datetime.now().strftime('%B %d, %Y')}",
            width=1200,
            height=800
        )

        # Update layout for better appearance
        fig.update_traces(
            hovertemplate='%{customdata[0]}<extra></extra>',
            textinfo='label+percent entry',
            marker=dict(
                line=dict(width=2, color='white')
            )
        )

        fig.update_layout(
            title={
                'text': f"Portfolio Allocation by Category<br><sub>{datetime.now().strftime('%B %d, %Y')}</sub>",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 24}
            },
            font=dict(size=12),
            margin=dict(t=100, l=0, r=0, b=0)
        )

        # Save as standalone HTML
        fig.write_html(
            output_path,
            include_plotlyjs='cdn',
            config={
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToRemove': ['pan2d', 'lasso2d']
            }
        )

        print(f"\n✓ Saved visualization to: {output_path}")
        return True

    except Exception as e:
        print(f"\nERROR creating visualization: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Create interactive portfolio allocation visualization'
    )
    parser.add_argument(
        '--data-dir',
        default='data',
        help='Directory containing data files (default: ./data)'
    )
    parser.add_argument(
        '--output-dir',
        default='dataviz',
        help='Directory for output files (default: ./dataviz)'
    )

    args = parser.parse_args()

    # Resolve paths
    data_dir = os.path.abspath(args.data_dir)
    output_dir = os.path.abspath(args.output_dir)

    print("=" * 60)
    print("Fidelity Portfolio Visualization")
    print("=" * 60)

    # Load data
    positions_df, mapping_df = load_data(data_dir)
    if positions_df is None or mapping_df is None:
        return 1

    # Merge and prepare data
    merged_df = merge_and_prepare_data(positions_df, mapping_df)
    if merged_df is None or len(merged_df) == 0:
        print("ERROR: No data to visualize")
        return 1

    # Create sunburst data structure
    print("\nBuilding hierarchical structure...")
    sunburst_df = create_sunburst_data(merged_df)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Generate visualization
    timestamp = datetime.now().strftime('%Y%m%d')
    output_file = os.path.join(output_dir, f'allocation_sunburst_{timestamp}.html')

    if create_sunburst_chart(sunburst_df, output_file):
        print("\n" + "=" * 60)
        print("SUCCESS: Visualization created!")
        print("=" * 60)
        print(f"\nOpen in browser: {output_file}")
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
