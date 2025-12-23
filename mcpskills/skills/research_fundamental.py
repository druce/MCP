#!/opt/anaconda3/envs/fidelity/bin/python3
"""
Fundamental Analysis Research Phase

Performs fundamental analysis using financial data from yfinance and OpenBB.

Usage:
    ./skills/research_fundamental.py SYMBOL [--work-dir DIR]

    If --work-dir is not specified, creates work/SYMBOL_YYYYMMDD automatically.

Examples:
    ./skills/research_fundamental.py TSLA
    ./skills/research_fundamental.py AAPL --work-dir custom/directory

Output:
    - Creates 02_fundamental/ directory in work directory
    - company_overview.json - Company information and metrics
    - income_statement.csv - Income statement data
    - balance_sheet.csv - Balance sheet data
    - cash_flow.csv - Cash flow statement
    - key_ratios.json - Financial ratios
    - analyst_recommendations.json - Analyst ratings
    - news.json - Recent news articles
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

# Financial data libraries
import yfinance as yf
import pandas as pd

# Load environment for OpenBB
from dotenv import load_dotenv
load_dotenv()

# OpenBB for additional data
from openbb import obb


def save_company_overview(symbol, work_dir):
    """
    Get and save company overview information.

    Args:
        symbol: Stock ticker symbol
        work_dir: Work directory path

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if output file already exists
        output_dir = os.path.join(work_dir, '02_fundamental')
        overview_path = os.path.join(output_dir, 'company_overview.json')

        if os.path.exists(overview_path):
            print(f"⊘ Company overview already exists, skipping: {overview_path}")
            return True

        print(f"Getting company overview for {symbol}...")

        # Get stock info from yfinance
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Extract key information
        overview = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'company_name': info.get('longName', 'N/A'),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'country': info.get('country', 'N/A'),
            'website': info.get('website', 'N/A'),
            'business_summary': info.get('longBusinessSummary', 'N/A'),
            'employees': info.get('fullTimeEmployees', 'N/A'),
            'market_cap': info.get('marketCap', 'N/A'),
            'enterprise_value': info.get('enterpriseValue', 'N/A'),
            'trailing_pe': info.get('trailingPE', 'N/A'),
            'forward_pe': info.get('forwardPE', 'N/A'),
            'peg_ratio': info.get('pegRatio', 'N/A'),
            'price_to_book': info.get('priceToBook', 'N/A'),
            'price_to_sales': info.get('priceToSalesTrailing12Months', 'N/A'),
            'profit_margin': info.get('profitMargins', 'N/A'),
            'operating_margin': info.get('operatingMargins', 'N/A'),
            'roe': info.get('returnOnEquity', 'N/A'),
            'roa': info.get('returnOnAssets', 'N/A'),
            'revenue': info.get('totalRevenue', 'N/A'),
            'revenue_per_share': info.get('revenuePerShare', 'N/A'),
            'quarterly_revenue_growth': info.get('revenueGrowth', 'N/A'),
            'gross_profit': info.get('grossProfits', 'N/A'),
            'ebitda': info.get('ebitda', 'N/A'),
            'net_income': info.get('netIncomeToCommon', 'N/A'),
            'eps': info.get('trailingEps', 'N/A'),
            'forward_eps': info.get('forwardEps', 'N/A'),
            'dividend_rate': info.get('dividendRate', 'N/A'),
            'dividend_yield': info.get('dividendYield', 'N/A'),
            'payout_ratio': info.get('payoutRatio', 'N/A'),
            'beta': info.get('beta', 'N/A'),
            '52_week_high': info.get('fiftyTwoWeekHigh', 'N/A'),
            '52_week_low': info.get('fiftyTwoWeekLow', 'N/A'),
            'shares_outstanding': info.get('sharesOutstanding', 'N/A'),
            'float_shares': info.get('floatShares', 'N/A'),
            'shares_short': info.get('sharesShort', 'N/A'),
            'short_ratio': info.get('shortRatio', 'N/A'),
            'short_percent_of_float': info.get('shortPercentOfFloat', 'N/A'),
            'held_percent_insiders': info.get('heldPercentInsiders', 'N/A'),
            'held_percent_institutions': info.get('heldPercentInstitutions', 'N/A'),
        }

        # Save to file
        os.makedirs(output_dir, exist_ok=True)

        with open(overview_path, 'w') as f:
            json.dump(overview, f, indent=2)

        print(f"✓ Saved company overview to: {overview_path}")
        print(f"  Company: {overview['company_name']}")
        print(f"  Sector: {overview['sector']}")
        print(f"  Industry: {overview['industry']}")

        return True

    except Exception as e:
        print(f"❌ Error getting company overview: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_financial_statements(symbol, work_dir):
    """
    Get and save financial statements.

    Args:
        symbol: Stock ticker symbol
        work_dir: Work directory path

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Getting financial statements for {symbol}...")

        ticker = yf.Ticker(symbol)
        output_dir = os.path.join(work_dir, '02_fundamental')
        os.makedirs(output_dir, exist_ok=True)

        # Income statement
        income_stmt = ticker.income_stmt
        if not income_stmt.empty:
            income_path = os.path.join(output_dir, 'income_statement.csv')
            income_stmt.to_csv(income_path)
            print(f"✓ Saved income statement to: {income_path}")

        # Balance sheet
        balance_sheet = ticker.balance_sheet
        if not balance_sheet.empty:
            balance_path = os.path.join(output_dir, 'balance_sheet.csv')
            balance_sheet.to_csv(balance_path)
            print(f"✓ Saved balance sheet to: {balance_path}")

        # Cash flow
        cash_flow = ticker.cashflow
        if not cash_flow.empty:
            cashflow_path = os.path.join(output_dir, 'cash_flow.csv')
            cash_flow.to_csv(cashflow_path)
            print(f"✓ Saved cash flow to: {cashflow_path}")

        return True

    except Exception as e:
        print(f"❌ Error getting financial statements: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_financial_ratios(symbol):
    """
    Retrieve comprehensive financial ratios for a given symbol using yfinance.

    Args:
        symbol: Stock ticker symbol

    Returns:
        DataFrame with columns: Category, Metric, {symbol}
    """
    ticker = yf.Ticker(symbol)
    info = ticker.info

    if not info:
        raise ValueError(f"No data available for symbol: {symbol}")

    # Organize ratios by category
    valuation_ratios = {
        'Trailing P/E': info.get('trailingPE'),
        'Forward P/E': info.get('forwardPE'),
        'PEG Ratio': info.get('pegRatio'),
        'Price/Sales (ttm)': info.get('priceToSalesTrailing12Months'),
        'Price/Book': info.get('priceToBook'),
        'Enterprise Value/Revenue': info.get('enterpriseToRevenue'),
        'Enterprise Value/EBITDA': info.get('enterpriseToEbitda'),
    }

    financial_highlights = {
        'Market Cap': info.get('marketCap'),
        'Enterprise Value': info.get('enterpriseValue'),
        'Revenue (ttm)': info.get('totalRevenue'),
        'Gross Profit (ttm)': info.get('grossProfits'),
        'EBITDA': info.get('ebitda'),
        'Net Income (ttm)': info.get('netIncomeToCommon'),
    }

    profitability_ratios = {
        'Profit Margin': info.get('profitMargins'),
        'Operating Margin': info.get('operatingMargins'),
        'Gross Margin': info.get('grossMargins'),
        'EBITDA Margin': info.get('ebitdaMargins'),
        'Return on Assets': info.get('returnOnAssets'),
        'Return on Equity': info.get('returnOnEquity'),
    }

    liquidity_ratios = {
        'Current Ratio': info.get('currentRatio'),
        'Quick Ratio': info.get('quickRatio'),
        'Total Cash': info.get('totalCash'),
        'Total Debt': info.get('totalDebt'),
        'Debt/Equity': info.get('debtToEquity'),
    }

    per_share_data = {
        'Earnings Per Share (ttm)': info.get('trailingEps'),
        'Book Value Per Share': info.get('bookValue'),
        'Revenue Per Share': info.get('revenuePerShare'),
        'Operating Cash Flow Per Share': (
            info.get('operatingCashflow', 0) / info['sharesOutstanding']
            if info.get('sharesOutstanding') and info['sharesOutstanding'] > 0
            else None
        ),
    }

    # Combine all categories
    all_ratios = {
        **valuation_ratios,
        **financial_highlights,
        **profitability_ratios,
        **liquidity_ratios,
        **per_share_data
    }

    # Create DataFrame
    df = pd.DataFrame(list(all_ratios.items()), columns=['Metric', symbol])
    df['Category'] = (
        ['Valuation'] * len(valuation_ratios) +
        ['Financial Highlights'] * len(financial_highlights) +
        ['Profitability'] * len(profitability_ratios) +
        ['Liquidity'] * len(liquidity_ratios) +
        ['Per Share'] * len(per_share_data)
    )
    return df[["Category", "Metric", symbol]]


def save_key_ratios(symbol, work_dir):
    """
    Calculate and save key financial ratios.

    Args:
        symbol: Stock ticker symbol
        work_dir: Work directory path

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Calculating key ratios for {symbol}...")

        # Get ratios for primary symbol
        symbol_df = get_financial_ratios(symbol)

        # Try to load peers list from 01_technical directory
        peers_list = []
        peers_path = os.path.join(work_dir, '01_technical', 'peers_list.json')

        print(f"\nLooking for peers at: {peers_path}")
        print(f"  File exists: {os.path.exists(peers_path)}")

        if os.path.exists(peers_path):
            try:
                with open(peers_path, 'r') as f:
                    peers_data = json.load(f)

                print(f"  Loaded peers JSON with keys: {list(peers_data.keys())}")

                # Extract peer symbols from the JSON structure
                # Handle different JSON structures:
                # 1. OpenBB format: {"symbol": ["ARWR", "MTSR", ...], "name": [...], ...}
                # 2. Results format: {"results": [{"symbol": "ARWR", ...}, ...]}
                # 3. Simple list: {"peers_list": ["ARWR", "MTSR", ...]}
                if 'symbol' in peers_data and isinstance(peers_data['symbol'], list):
                    peers_list = [s for s in peers_data['symbol'] if s]
                    print(f"  Extracted {len(peers_list)} peers from 'symbol' field")
                elif 'results' in peers_data and isinstance(peers_data['results'], list):
                    peers_list = [p.get('symbol') for p in peers_data['results'] if p.get('symbol')]
                    print(f"  Extracted {len(peers_list)} peers from 'results' field")
                elif 'peers_list' in peers_data and isinstance(peers_data['peers_list'], list):
                    peers_list = peers_data['peers_list']
                    print(f"  Extracted {len(peers_list)} peers from 'peers_list' field")

                if peers_list:
                    print(f"✓ Found {len(peers_list)} peers: {', '.join(peers_list[:5])}{'...' if len(peers_list) > 5 else ''}")
                else:
                    print(f"⚠ No peers extracted from JSON")
            except Exception as e:
                print(f"⚠ Could not load peers list: {e}")
                print("  Continuing with just the main symbol...")
                import traceback
                traceback.print_exc()
        else:
            print(f"⊘ No peers list found")
            print("  Continuing with just the main symbol...")

        # Get ratios for each peer
        peers_dflist = []
        for peer in peers_list:
            try:
                peer_df = get_financial_ratios(peer)
                # Only keep the last column (the data column)
                peers_dflist.append(peer_df.iloc[:, 2])
                print(f"  ✓ Got ratios for {peer}")
            except Exception as e:
                print(f"  ⚠ Could not get ratios for {peer}: {e}")
                continue

        # Concatenate original table with peer data
        if peers_dflist:
            df = pd.concat([symbol_df] + peers_dflist, axis=1)
        else:
            df = symbol_df

        # Save to CSV
        output_dir = os.path.join(work_dir, '02_fundamental')
        os.makedirs(output_dir, exist_ok=True)

        ratios_path = os.path.join(output_dir, 'key_ratios.csv')
        df.to_csv(ratios_path, index=False)

        print(f"✓ Saved key ratios to: {ratios_path}")
        print(f"  Columns: {', '.join(df.columns.tolist())}")
        print(f"  Rows: {len(df)} ratios")

        return True

    except Exception as e:
        print(f"❌ Error calculating key ratios: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_analyst_recommendations(symbol, work_dir):
    """
    Get and save analyst recommendations.

    Args:
        symbol: Stock ticker symbol
        work_dir: Work directory path

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Getting analyst recommendations for {symbol}...")

        ticker = yf.Ticker(symbol)
        recommendations = ticker.recommendations

        if recommendations is not None and not recommendations.empty:
            output_dir = os.path.join(work_dir, '02_fundamental')
            os.makedirs(output_dir, exist_ok=True)

            # Convert to JSON-serializable format
            recs_dict = recommendations.tail(20).to_dict(orient='records')

            # Convert timestamps to strings
            for rec in recs_dict:
                for key, value in rec.items():
                    if pd.isna(value):
                        rec[key] = None
                    elif hasattr(value, 'isoformat'):
                        rec[key] = value.isoformat()

            recs_path = os.path.join(output_dir, 'analyst_recommendations.json')
            with open(recs_path, 'w') as f:
                json.dump(recs_dict, f, indent=2)

            print(f"✓ Saved analyst recommendations to: {recs_path}")
            print(f"  Total recommendations: {len(recs_dict)}")
        else:
            print("⊘ No analyst recommendations available")

        return True

    except Exception as e:
        print(f"❌ Error getting analyst recommendations: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_news(symbol, work_dir):
    """
    Get and save recent news articles.

    Args:
        symbol: Stock ticker symbol
        work_dir: Work directory path

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Getting recent news for {symbol}...")

        ticker = yf.Ticker(symbol)
        news = ticker.news

        if news:
            output_dir = os.path.join(work_dir, '02_fundamental')
            os.makedirs(output_dir, exist_ok=True)

            news_path = os.path.join(output_dir, 'news.json')
            with open(news_path, 'w') as f:
                json.dump(news, f, indent=2)

            print(f"✓ Saved news to: {news_path}")
            print(f"  Total articles: {len(news)}")
        else:
            print("⊘ No news available")

        return True

    except Exception as e:
        print(f"❌ Error getting news: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Fundamental analysis research phase'
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

    print("=" * 60)
    print("Fundamental Analysis Phase")
    print("=" * 60)
    print(f"Symbol: {symbol}")
    print(f"Work Directory: {work_dir}")
    print("=" * 60)

    success_count = 0
    total_count = 5

    # Task 1: Company overview
    if save_company_overview(symbol, work_dir):
        success_count += 1

    # Task 2: Financial statements
    if save_financial_statements(symbol, work_dir):
        success_count += 1

    # Task 3: Key ratios
    if save_key_ratios(symbol, work_dir):
        success_count += 1

    # Task 4: Analyst recommendations
    if save_analyst_recommendations(symbol, work_dir):
        success_count += 1

    # Task 5: News
    if save_news(symbol, work_dir):
        success_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("Fundamental Analysis Phase Complete")
    print("=" * 60)
    print(f"Tasks completed: {success_count}/{total_count}")

    if success_count == total_count:
        print("✓ All tasks completed successfully")
        return 0
    elif success_count > 0:
        print(f"⚠ Partial success: {success_count}/{total_count} tasks completed")
        return 0  # Still return success for partial completion
    else:
        print("❌ All tasks failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
