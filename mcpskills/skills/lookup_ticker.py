#!/opt/anaconda3/envs/mcpskills/bin/python3
"""
OpenBB Ticker Lookup Skill

Searches for stock ticker symbols by company name using the OpenBB API.

Usage:
    ./skills/lookup_ticker.py "company name"
    ./skills/lookup_ticker.py "Broadcom"
    ./skills/lookup_ticker.py --query "Apple Inc" --limit 5

Output:
    - Prints matching ticker symbols with company names
    - Optionally saves results to CSV file
"""

import sys
import argparse
import pandas as pd
from datetime import datetime
import os
from openbb import obb
from dotenv import load_dotenv


def search_ticker(query, provider='cboe', limit=10, pat=None):
    """
    Search for ticker symbols using OpenBB Platform.

    Args:
        query (str): Company name or search string
        provider (str): Data provider (default: 'cboe')
        limit (int): Maximum number of results to return
        pat (str): OpenBB Personal Access Token (optional)

    Returns:
        list: List of dictionaries with ticker information
    """
    try:
        # Login with PAT if provided
        if pat:
            try:
                obb.user.credentials.openbb_pat = pat
            except Exception as e:
                print(f"Warning: Could not login with PAT: {e}")

        print(f"Searching for: '{query}' (provider: {provider})")

        # Use OpenBB equity search
        result = obb.equity.search(query=query, provider=provider)

        # Convert result to list of dictionaries
        if hasattr(result, 'to_dataframe'):
            # Convert OBBject to DataFrame then to records
            df = result.to_dataframe()
            results = df.to_dict('records')
        elif hasattr(result, 'results'):
            # Some results have a .results attribute
            results = result.results
            if not isinstance(results, list):
                # If results is not a list, try to convert
                try:
                    df = pd.DataFrame([results])
                    results = df.to_dict('records')
                except:
                    results = [results]
        elif isinstance(result, list):
            results = result
        else:
            print(f"Unexpected result format: {type(result)}")
            return []

        # Limit results
        if limit and len(results) > limit:
            results = results[:limit]

        return results

    except ImportError:
        print("ERROR: OpenBB not installed. Install with: pip install openbb")
        return []
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return []


def format_results(results):
    """
    Format search results for display.

    Args:
        results (list): List of ticker information dictionaries

    Returns:
        pd.DataFrame: Formatted results
    """
    if not results:
        return None

    # Convert to DataFrame for nice formatting
    df = pd.DataFrame(results)

    # Common fields to display (adjust based on actual API response)
    # Priority order for columns
    priority_cols = ['symbol', 'name', 'exchange', 'dpm_name', 'post_station',
                     'type', 'market_cap', 'country', 'cik']
    display_cols = []

    for col in priority_cols:
        if col in df.columns:
            display_cols.append(col)

    # Add any remaining columns not in priority list
    for col in df.columns:
        if col not in display_cols:
            display_cols.append(col)

    if display_cols:
        df = df[display_cols]

    return df


def save_results(df, output_dir='data'):
    """
    Save search results to CSV file.

    Args:
        df (pd.DataFrame): Search results
        output_dir (str): Directory to save file

    Returns:
        str: Path to saved file
    """
    if df is None or len(df) == 0:
        return None

    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'ticker_search_{timestamp}.csv')

    df.to_csv(output_file, index=False)
    return output_file


def main():
    """Main execution function."""
    # Load environment variables from .env file
    load_dotenv()

    # login using PAT from environment variable
    openbb_pat = os.getenv('OPENBB_PAT')
    if not openbb_pat:
        raise ValueError("OPENBB_PAT environment variable not set")
    obb.user.credentials.openbb_pat = openbb_pat


    parser = argparse.ArgumentParser(
        description='Search for stock ticker symbols by company name using OpenBB API'
    )
    parser.add_argument(
        'query',
        nargs='?',
        help='Company name or search string (e.g., "Broadcom")'
    )
    parser.add_argument(
        '--query', '-q',
        dest='query_flag',
        help='Company name or search string (alternative format)'
    )
    parser.add_argument(
        '--provider', '-p',
        default='cboe',
        help='Data provider (default: cboe, options: cboe, nasdaq, sec)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=10,
        help='Maximum number of results (default: 10)'
    )
    parser.add_argument(
        '--api-key', '-k',
        help='OpenBB PAT (or set OPENBB_PAT environment variable)'
    )
    parser.add_argument(
        '--save', '-s',
        action='store_true',
        help='Save results to CSV file in data/ directory'
    )
    parser.add_argument(
        '--output-dir', '-o',
        default='data',
        help='Directory to save results (default: data)'
    )

    args = parser.parse_args()

    # Get query from either positional or flag argument
    query = args.query or args.query_flag

    if not query:
        parser.print_help()
        print("\nERROR: Please provide a company name to search for")
        print("Example: ./skills/lookup_ticker.py \"Broadcom\"")
        return 1

    # Get PAT from argument or environment
    pat = args.api_key or os.environ.get('OPENBB_PAT')

    print("=" * 60)
    print("OpenBB Ticker Lookup")
    print("=" * 60)

    if not pat:
        print("\nWARNING: No PAT provided. Some providers may require authentication.")
        print("Set OPENBB_PAT environment variable or use --api-key flag\n")

    # Search for ticker
    results = search_ticker(query, args.provider, args.limit, pat)

    if not results:
        print("\n" + "=" * 60)
        print("No results found")
        print("=" * 60)
        return 0

    # Format and display results
    df = format_results(results)

    print(f"\nFound {len(results)} result(s):\n")

    if df is not None:
        print(df.to_string(index=False))
    else:
        # Fallback: print raw results
        for i, result in enumerate(results, 1):
            print(f"{i}. {result}")

    # Save if requested
    if args.save and df is not None:
        saved_file = save_results(df, args.output_dir)
        if saved_file:
            print(f"\n✓ Results saved to: {saved_file}")

    print("\n" + "=" * 60)
    print("SUCCESS: Ticker lookup complete!")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
