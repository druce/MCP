#!/opt/anaconda3/envs/mcpskills/bin/python3
"""
Wikipedia Research Phase

Fetches company information from Wikipedia.

Usage:
    ./skills/research_wikipedia.py SYMBOL [--work-dir DIR]

    If --work-dir is not specified, creates work/SYMBOL_YYYYMMDD automatically.

Examples:
    ./skills/research_wikipedia.py TSLA
    ./skills/research_wikipedia.py AAPL --work-dir custom/directory

Output:
    - Creates 06_wikipedia/ directory in work directory
    - wikipedia_summary.txt - Page summary
    - wikipedia_infobox.json - Structured infobox data
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

# Wikipedia API
import wikipediaapi

# Yahoo Finance for company name lookup
import yfinance as yf


def get_company_name(symbol, work_dir):
    """
    Get company name for a symbol, trying multiple sources.

    Priority:
    1. Try loading from company_overview.json (if fundamental phase ran first)
    2. Fall back to fetching directly from yfinance

    Args:
        symbol: Stock ticker symbol
        work_dir: Work directory path

    Returns:
        str: Company name or symbol if not found
    """
    # Try loading from fundamentals first
    company_overview_path = os.path.join(work_dir, '02_fundamental', 'company_overview.json')
    if os.path.exists(company_overview_path):
        try:
            with open(company_overview_path, 'r') as f:
                overview = json.load(f)
                company_name = overview.get('company_name', None)
                if company_name and company_name != 'N/A':
                    return company_name
        except Exception as e:
            print(f"  ⚠ Could not load company name from fundamentals: {e}")

    # Fall back to yfinance lookup
    try:
        print(f"  Looking up company name for {symbol}...")
        ticker = yf.Ticker(symbol)
        info = ticker.info
        company_name = info.get('longName', None)
        if company_name:
            print(f"  ✓ Found: {company_name}")
            return company_name
    except Exception as e:
        print(f"  ⚠ Could not fetch company name from yfinance: {e}")

    # If all else fails, return the symbol
    print(f"  ⚠ Using symbol as fallback")
    return symbol


def fetch_wikipedia_data(symbol, work_dir, company_name=None):
    """
    Fetch Wikipedia data for the company.

    Args:
        symbol: Stock ticker symbol
        work_dir: Work directory path
        company_name: Optional company name from metadata/yfinance

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        identifier = company_name if company_name else symbol
        print(f"Fetching Wikipedia data for {identifier}...")

        # Initialize Wikipedia API
        wiki = wikipediaapi.Wikipedia(
            language='en',
            user_agent='FidelityPortfolioResearch/1.0'
        )

        # Try different search patterns, using company name if available
        search_attempts = []

        if company_name and company_name != symbol:
            # If we have a company name, try it first
            search_attempts.append(company_name)
            # Also try with "(company)" suffix
            search_attempts.append(f"{company_name} (company)")

        # Add fallback patterns with symbol
        search_attempts.extend([
            f"{symbol} (company)",
            f"{symbol} Inc.",
            symbol
        ])

        # Try to get the page with each search pattern
        page = None
        for search_term in search_attempts:
            page = wiki.page(search_term)
            if page.exists():
                break

        if not page or not page.exists():
            print(f"❌ Wikipedia page not found for {symbol}")
            print(f"   Tried: {', '.join(search_attempts)}")
            return False

        print(f"  Found Wikipedia page: {page.title}")

        output_dir = os.path.join(work_dir, '06_wikipedia')
        os.makedirs(output_dir, exist_ok=True)

        # Save summary
        summary_path = os.path.join(output_dir, 'wikipedia_summary.txt')
        with open(summary_path, 'w') as f:
            f.write(f"Wikipedia Summary - {symbol}\n")
            f.write(f"=" * 60 + "\n\n")
            f.write(f"Page Title: {page.title}\n")
            f.write(f"URL: {page.fullurl}\n")
            f.write(f"Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"=" * 60 + "\n\n")
            f.write(page.summary)
            f.write("\n\n")
            f.write(f"=" * 60 + "\n")
            f.write(f"Full Article URL: {page.fullurl}\n")

        print(f"✓ Saved Wikipedia summary to: {summary_path}")

        # Save metadata
        metadata = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'page_title': page.title,
            'page_url': page.fullurl,
            'summary_length': len(page.summary),
            'full_text_length': len(page.text),
        }

        metadata_path = os.path.join(output_dir, 'wikipedia_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"✓ Saved Wikipedia metadata to: {metadata_path}")

        return True

    except Exception as e:
        print(f"❌ Error fetching Wikipedia data: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Wikipedia research phase'
    )
    parser.add_argument(
        'symbol',
        help='Stock ticker symbol (e.g., TSLA, AAPL, MSFT)'
    )
    parser.add_argument(
        '--work-dir',
        default=None,
        help='Work directory path (default: work/SYMBOL_YYYYMMDD)'
    )

    args = parser.parse_args()

    # Normalize symbol
    symbol = args.symbol.upper()

    # Generate work directory if not specified
    if not args.work_dir:
        date_str = datetime.now().strftime('%Y%m%d')
        work_dir = os.path.join('work', f'{symbol}_{date_str}')
    else:
        work_dir = args.work_dir

    # Create work directory if it doesn't exist
    os.makedirs(work_dir, exist_ok=True)

    # Get company name for better Wikipedia searches
    company_name = get_company_name(symbol, work_dir)

    print("=" * 60)
    print("Wikipedia Research Phase")
    print("=" * 60)
    print(f"Symbol: {symbol}")
    print(f"Company: {company_name}")
    print(f"Work Directory: {work_dir}")
    print("=" * 60)

    success_count = 0
    total_count = 1

    # Task 1: Fetch Wikipedia data
    if fetch_wikipedia_data(symbol, work_dir, company_name):
        success_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("Wikipedia Research Phase Complete")
    print("=" * 60)
    print(f"Tasks completed: {success_count}/{total_count}")

    if success_count == total_count:
        print("✓ All tasks completed successfully")
        return 0
    elif success_count > 0:
        print(f"⚠ Partial success: {success_count}/{total_count} tasks completed")
        return 0
    else:
        print("❌ All tasks failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
