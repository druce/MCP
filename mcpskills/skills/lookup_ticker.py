#!/opt/anaconda3/envs/mcpskills/bin/python3
"""
Ticker Lookup Skill with Multi-Provider Fallback

Searches for stock ticker symbols by company name using:
1. yfinance (primary - free, no API key required)
2. Finnhub (secondary - free tier with API key)
3. OpenBB+FMP (fallback - requires PAT, FMP may need paid subscription)

Usage:
    ./skills/lookup_ticker.py "company name"
    ./skills/lookup_ticker.py "Broadcom"
    ./skills/lookup_ticker.py --query "Apple Inc" --limit 5

Output:
    - Prints matching ticker symbols with company names
    - Optionally saves results to CSV file
    - Shows which provider was used
"""

import sys
import argparse
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv


def search_ticker_yfinance(query, limit=10):
    """
    Search for ticker symbols using yfinance.

    Note: yfinance doesn't have a native search API, but we can validate
    if a symbol exists by trying to fetch its info.

    Args:
        query (str): Ticker symbol or company name
        limit (int): Maximum number of results to return

    Returns:
        tuple: (success: bool, results: list, error: str)
    """
    try:
        import yfinance as yf

        # yfinance doesn't have search, but we can try to validate a symbol
        # If query looks like a symbol (short, uppercase), validate it
        if len(query) <= 5 and query.replace('.', '').isalpha():
            ticker = yf.Ticker(query.upper())
            try:
                info = ticker.info

                # Check if we got valid data
                if info and 'symbol' in info:
                    results = [{
                        'symbol': info.get('symbol', query.upper()),
                        'name': info.get('longName', info.get('shortName', 'N/A')),
                        'exchange': info.get('exchange', 'N/A'),
                        'type': info.get('quoteType', 'N/A'),
                        'currency': info.get('currency', 'N/A'),
                        'country': info.get('country', 'N/A')
                    }]
                    return True, results, None
            except:
                pass

        # yfinance doesn't support company name search
        return False, [], "yfinance doesn't support company name search, only symbol validation"

    except ImportError:
        return False, [], "yfinance not installed"
    except Exception as e:
        return False, [], f"yfinance error: {str(e)}"


def search_ticker_finnhub(query, limit=10):
    """
    Search for ticker symbols using Finnhub API.

    Args:
        query (str): Company name or ticker symbol
        limit (int): Maximum number of results to return

    Returns:
        tuple: (success: bool, results: list, error: str)
    """
    try:
        import finnhub

        api_key = os.getenv('FINNHUB_API_KEY')
        if not api_key:
            return False, [], "FINNHUB_API_KEY not set in environment"

        client = finnhub.Client(api_key=api_key)

        # Use symbol lookup endpoint
        search_results = client.symbol_lookup(query)

        if not search_results or 'result' not in search_results:
            return False, [], "No results from Finnhub"

        raw_results = search_results['result']

        if not raw_results:
            return False, [], "Finnhub returned empty results"

        # Format results
        results = []
        for item in raw_results[:limit]:
            results.append({
                'symbol': item.get('symbol', 'N/A'),
                'name': item.get('description', 'N/A'),
                'type': item.get('type', 'N/A'),
                'exchange': item.get('displaySymbol', 'N/A'),
                'mic': item.get('mic', 'N/A')
            })

        return True, results, None

    except ImportError:
        return False, [], "finnhub-python not installed (pip install finnhub-python)"
    except Exception as e:
        error_msg = str(e)
        # Check for rate limit
        if '429' in error_msg or 'rate limit' in error_msg.lower():
            return False, [], f"Finnhub rate limit exceeded: {error_msg}"
        return False, [], f"Finnhub error: {error_msg}"


def search_ticker_openbb(query, provider='cboe', limit=10):
    """
    Search for ticker symbols using OpenBB Platform.

    Args:
        query (str): Company name or search string
        provider (str): Data provider (default: 'cboe')
        limit (int): Maximum number of results to return

    Returns:
        tuple: (success: bool, results: list, error: str)
    """
    try:
        from openbb import obb

        pat = os.getenv('OPENBB_PAT')
        if not pat:
            return False, [], "OPENBB_PAT not set in environment"

        # Login with PAT
        try:
            obb.user.credentials.openbb_pat = pat
        except Exception as e:
            return False, [], f"Could not login with PAT: {e}"

        # Use OpenBB equity search
        result = obb.equity.search(query=query, provider=provider)

        # Convert result to list of dictionaries
        if hasattr(result, 'to_dataframe'):
            df = result.to_dataframe()
            results = df.to_dict('records')
        elif hasattr(result, 'results'):
            results = result.results
            if not isinstance(results, list):
                try:
                    df = pd.DataFrame([results])
                    results = df.to_dict('records')
                except:
                    results = [results]
        elif isinstance(result, list):
            results = result
        else:
            return False, [], f"Unexpected result format: {type(result)}"

        # Limit results
        if limit and len(results) > limit:
            results = results[:limit]

        if not results:
            return False, [], "OpenBB returned empty results"

        return True, results, None

    except ImportError:
        return False, [], "OpenBB not installed (pip install openbb)"
    except Exception as e:
        return False, [], f"OpenBB error: {str(e)}"


def search_ticker_with_fallback(query, limit=10, provider='cboe'):
    """
    Search for ticker symbols with automatic fallback chain:
    yfinance -> Finnhub -> OpenBB+FMP

    Args:
        query (str): Company name or ticker symbol
        limit (int): Maximum number of results
        provider (str): OpenBB provider (only used if we fall back to OpenBB)

    Returns:
        tuple: (results: list, provider_used: str, all_errors: dict)
    """
    all_errors = {}

    # Try yfinance first
    print(f"[1/3] Trying yfinance...")
    success, results, error = search_ticker_yfinance(query, limit)
    all_errors['yfinance'] = error

    if success and results:
        print(f"✓ yfinance succeeded ({len(results)} results)")
        return results, 'yfinance', all_errors
    else:
        print(f"✗ yfinance failed: {error}")

    # Try Finnhub second
    print(f"[2/3] Trying Finnhub...")
    success, results, error = search_ticker_finnhub(query, limit)
    all_errors['finnhub'] = error

    if success and results:
        print(f"✓ Finnhub succeeded ({len(results)} results)")
        return results, 'Finnhub', all_errors
    else:
        print(f"✗ Finnhub failed: {error}")

    # Try OpenBB+FMP last
    print(f"[3/3] Trying OpenBB+FMP...")
    success, results, error = search_ticker_openbb(query, provider, limit)
    all_errors['openbb'] = error

    if success and results:
        print(f"✓ OpenBB+FMP succeeded ({len(results)} results)")
        return results, f'OpenBB+FMP (provider={provider})', all_errors
    else:
        print(f"✗ OpenBB+FMP failed: {error}")

    # All providers failed
    return [], 'none', all_errors


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
    priority_cols = ['symbol', 'name', 'exchange', 'type', 'mic',
                     'market_cap', 'country', 'currency', 'dpm_name',
                     'post_station', 'cik']
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

    parser = argparse.ArgumentParser(
        description='Search for stock ticker symbols with multi-provider fallback'
    )
    parser.add_argument(
        'query',
        nargs='?',
        help='Company name or ticker symbol (e.g., "Broadcom" or "AVGO")'
    )
    parser.add_argument(
        '--query', '-q',
        dest='query_flag',
        help='Company name or ticker symbol (alternative format)'
    )
    parser.add_argument(
        '--provider', '-p',
        default='cboe',
        help='OpenBB data provider (only used as fallback, default: cboe)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=10,
        help='Maximum number of results (default: 10)'
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
        print("\nERROR: Please provide a company name or ticker symbol to search for")
        print("Example: ./skills/lookup_ticker.py \"Broadcom\"")
        print("Example: ./skills/lookup_ticker.py \"AVGO\"")
        return 1

    print("=" * 60)
    print("Multi-Provider Ticker Lookup")
    print("=" * 60)
    print(f"\nSearching for: '{query}'")
    print(f"Fallback chain: yfinance → Finnhub → OpenBB+FMP\n")

    # Search with fallback
    results, provider_used, all_errors = search_ticker_with_fallback(
        query,
        args.limit,
        args.provider
    )

    if not results:
        print("\n" + "=" * 60)
        print("ERROR: No results found from any provider")
        print("=" * 60)
        print("\nProvider errors:")
        for provider, error in all_errors.items():
            if error:
                print(f"  • {provider}: {error}")
        print("\nTroubleshooting:")
        print("  1. Check if ticker symbol is correct")
        print("  2. Set FINNHUB_API_KEY in .env (get free key at https://finnhub.io/register)")
        print("  3. Set OPENBB_PAT in .env")
        print("=" * 60)
        return 1

    # Format and display results
    df = format_results(results)

    print(f"\n{'=' * 60}")
    print(f"SUCCESS: Found {len(results)} result(s) using {provider_used}")
    print("=" * 60)

    if df is not None:
        print("\n" + df.to_string(index=False))
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

    return 0


if __name__ == '__main__':
    sys.exit(main())
