#!/opt/anaconda3/envs/mcpskills/bin/python3
"""
Technical Analysis Research Phase

Performs technical analysis using charts and indicators from the MCP server.

Usage:
    ./skills/research_technical.py SYMBOL [--work-dir DIR]

    If --work-dir is not specified, creates work/SYMBOL_YYYYMMDD automatically.

Examples:
    ./skills/research_technical.py INTC
    ./skills/research_technical.py AAPL --work-dir custom/directory

Output:
    - Creates 01_technical/ directory in work directory
    - chart.png - Stock chart with technical indicators
    - technical_analysis.json - Technical indicators data
    - peers_list.json - List of peer companies
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
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import talib

# Load environment for OpenBB
from dotenv import load_dotenv
load_dotenv()

# OpenBB for peer data
from openbb import obb


# ============================================================================
# Peer Lookup Helper Functions
# ============================================================================

def get_peers_finnhub(symbol):
    """
    Get peer companies using Finnhub API.

    Args:
        symbol: Stock ticker symbol

    Returns:
        tuple: (success: bool, peers_data: dict, error: str)
    """
    try:
        import finnhub

        api_key = os.getenv('FINNHUB_API_KEY')
        if not api_key:
            return False, {}, "FINNHUB_API_KEY not set in environment"

        client = finnhub.Client(api_key=api_key)

        # Get peer tickers (uses GICS sub-industry classification)
        peer_symbols = client.company_peers(symbol)

        # Remove the target symbol if it's in the list
        peer_symbols = [s for s in peer_symbols if s != symbol]

        if not peer_symbols:
            return False, {}, "Finnhub returned no peers"

        print(f"  Found {len(peer_symbols)} potential peers from Finnhub: {', '.join(peer_symbols[:5])}...")

        # Enrich with yfinance data
        peers_data = {
            'symbol': [],
            'name': [],
            'price': [],
            'market_cap': []
        }

        for peer in peer_symbols[:15]:  # Limit to top 15
            try:
                ticker = yf.Ticker(peer)
                info = ticker.info

                peers_data['symbol'].append(peer)
                peers_data['name'].append(info.get('longName', peer))
                price = info.get('currentPrice') or info.get('regularMarketPrice', 0.0)
                peers_data['price'].append(float(price) if price else 0.0)
                peers_data['market_cap'].append(info.get('marketCap', 0))

            except Exception as e:
                print(f"  ⚠ Could not fetch data for {peer}: {e}")
                continue

        if not peers_data['symbol']:
            return False, {}, "Could not enrich any peers with market data"

        print(f"  ✓ Enriched {len(peers_data['symbol'])} peers with market data")
        return True, peers_data, None

    except ImportError:
        return False, {}, "finnhub-python not installed (pip install finnhub-python)"
    except Exception as e:
        error_msg = str(e)
        # Check for rate limit
        if '429' in error_msg or 'rate limit' in error_msg.lower():
            return False, {}, f"Finnhub rate limit exceeded: {error_msg}"
        return False, {}, f"Finnhub error: {error_msg}"


def get_peers_openbb(symbol):
    """
    Get peer companies using OpenBB/FMP.

    Args:
        symbol: Stock ticker symbol

    Returns:
        tuple: (success: bool, peers_data: dict, error: str)
    """
    try:
        pat = os.getenv('OPENBB_PAT')
        if not pat:
            return False, {}, "OPENBB_PAT not set in environment"

        # Login with PAT
        try:
            obb.user.credentials.openbb_pat = pat
        except Exception as e:
            return False, {}, f"Could not login with PAT: {e}"

        # Get peers using FMP provider
        peers_result = obb.equity.compare.peers(symbol=symbol, provider='fmp')
        peers_data = peers_result.to_dict()

        if not peers_data:
            return False, {}, "OpenBB/FMP returned empty results"

        print(f"  ✓ OpenBB/FMP returned peers")
        return True, peers_data, None

    except ImportError:
        return False, {}, "OpenBB not installed (pip install openbb)"
    except Exception as e:
        error_msg = str(e)
        # Check if it's a subscription issue
        if 'subscription' in error_msg.lower() or 'plan' in error_msg.lower():
            return False, {}, f"FMP peers endpoint requires paid subscription: {error_msg}"
        return False, {}, f"OpenBB/FMP error: {error_msg}"


def get_peers_with_fallback(symbol):
    """
    Get peer companies with automatic fallback chain:
    Finnhub -> OpenBB+FMP

    Args:
        symbol: Stock ticker symbol

    Returns:
        tuple: (peers_data: dict, provider_used: str, all_errors: dict)
    """
    all_errors = {}

    # Try Finnhub first
    print(f"[1/2] Trying Finnhub for peer detection...")
    success, peers_data, error = get_peers_finnhub(symbol)
    all_errors['finnhub'] = error

    if success and peers_data:
        print(f"✓ Finnhub succeeded")
        return peers_data, 'Finnhub', all_errors
    else:
        print(f"✗ Finnhub failed: {error}")

    # Try OpenBB+FMP second
    print(f"[2/2] Trying OpenBB+FMP for peer detection...")
    success, peers_data, error = get_peers_openbb(symbol)
    all_errors['openbb'] = error

    if success and peers_data:
        print(f"✓ OpenBB+FMP succeeded")
        return peers_data, 'OpenBB+FMP', all_errors
    else:
        print(f"✗ OpenBB+FMP failed: {error}")

    # All providers failed
    return {'symbol': [], 'name': [], 'price': [], 'market_cap': []}, 'none', all_errors


# ============================================================================
# Chart and Technical Analysis Functions
# ============================================================================

def save_chart(symbol, work_dir):
    """
    Generate and save stock chart.

    Args:
        symbol: Stock ticker symbol
        work_dir: Work directory path

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Generating stock chart for {symbol}...")

        # Download weekly data
        symbol_df = yf.download(symbol, interval="1wk", period="4y", progress=False)
        spx_df = yf.download("^GSPC", interval="1wk", period="4y", progress=False)

        if symbol_df.empty:
            print(f"❌ No data available for {symbol}")
            return False

        # Flatten multi-index columns if present
        if isinstance(symbol_df.columns, pd.MultiIndex):
            symbol_df.columns = symbol_df.columns.get_level_values(0)
        if isinstance(spx_df.columns, pd.MultiIndex):
            spx_df.columns = spx_df.columns.get_level_values(0)

        # Compute moving averages
        symbol_df['MA13'] = symbol_df['Close'].rolling(window=13).mean()
        symbol_df['MA52'] = symbol_df['Close'].rolling(window=52).mean()

        # Compute relative strength vs SPX
        relative = (symbol_df['Close'] / spx_df['Close']).values
        symbol_df['Rel_SPX'] = relative

        # Create figure with subplots
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            row_heights=[0.75, 0.25],
            vertical_spacing=0.02,
            specs=[[{"secondary_y": True}], [{}]]
        )

        # Candlestick chart
        colors = ['green' if row['Close'] >= row['Open'] else 'red'
                  for idx, row in symbol_df.iterrows()]

        fig.add_trace(
            go.Candlestick(
                x=symbol_df.index,
                open=symbol_df['Open'],
                high=symbol_df['High'],
                low=symbol_df['Low'],
                close=symbol_df['Close'],
                increasing_line_color='green',
                decreasing_line_color='red',
                name=symbol
            ),
            row=1, col=1
        )

        # Moving averages
        fig.add_trace(
            go.Scatter(x=symbol_df.index, y=symbol_df['MA13'],
                       mode='lines', name='MA13', line=dict(color='blue', width=1)),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(x=symbol_df.index, y=symbol_df['MA52'],
                       mode='lines', name='MA52', line=dict(color='orange', width=1)),
            row=1, col=1
        )

        # Volume
        fig.add_trace(
            go.Bar(x=symbol_df.index, y=symbol_df['Volume'],
                   name='Volume', marker_color=colors, opacity=0.5),
            row=1, col=1, secondary_y=True
        )

        # Relative strength
        fig.add_trace(
            go.Scatter(x=symbol_df.index, y=symbol_df['Rel_SPX'],
                       mode='lines', name='Rel. to S&P500',
                       line=dict(color='purple', width=1)),
            row=2, col=1
        )

        # Update layout
        fig.update_layout(
            title=f'{symbol} - Weekly Chart',
            xaxis_rangeslider_visible=False,
            height=600,
            width=800,
            showlegend=True
        )

        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=1, col=1, secondary_y=True)
        fig.update_yaxes(title_text="Relative Strength", row=2, col=1)

        # Save chart
        output_dir = os.path.join(work_dir, '01_technical')
        os.makedirs(output_dir, exist_ok=True)

        chart_path = os.path.join(output_dir, 'chart.png')
        fig.write_image(chart_path, scale=2)

        print(f"✓ Saved chart to: {chart_path}")
        return True

    except Exception as e:
        print(f"❌ Error generating chart: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_technical_analysis(symbol, work_dir):
    """
    Generate and save technical analysis indicators.

    Args:
        symbol: Stock ticker symbol
        work_dir: Work directory path

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Running technical analysis for {symbol}...")

        # Download daily data for technical indicators
        df = yf.download(symbol, period="1y", progress=False)

        if df.empty:
            print(f"❌ No data available for {symbol}")
            return False

        # Flatten multi-index columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Calculate technical indicators using TA-Lib
        # Convert to numpy arrays and ensure they are 1D
        close = np.array(df['Close'].values, dtype=np.float64).flatten()
        high = np.array(df['High'].values, dtype=np.float64).flatten()
        low = np.array(df['Low'].values, dtype=np.float64).flatten()
        volume = np.array(df['Volume'].values, dtype=np.float64).flatten()

        # Moving averages
        sma_20 = talib.SMA(close, timeperiod=20)
        sma_50 = talib.SMA(close, timeperiod=50)
        sma_200 = talib.SMA(close, timeperiod=200)

        # RSI (14-period)
        rsi = talib.RSI(close, timeperiod=14)

        # MACD (12, 26, 9)
        macd, macd_signal, macd_hist = talib.MACD(close,
                                                    fastperiod=12,
                                                    slowperiod=26,
                                                    signalperiod=9)

        # ATR (14-period)
        atr = talib.ATR(high, low, close, timeperiod=14)

        # Bollinger Bands (optional - for additional context)
        bb_upper, bb_middle, bb_lower = talib.BBANDS(close,
                                                       timeperiod=20,
                                                       nbdevup=2,
                                                       nbdevdn=2,
                                                       matype=0)

        # Get latest values - convert immediately to floats
        price_val = float(close[-1])
        rsi_val = float(rsi[-1]) if not np.isnan(rsi[-1]) else 0.0
        atr_val = float(atr[-1]) if not np.isnan(atr[-1]) else 0.0
        macd_val = float(macd[-1]) if not np.isnan(macd[-1]) else 0.0
        macd_sig_val = float(macd_signal[-1]) if not np.isnan(macd_signal[-1]) else 0.0
        macd_hist_val = float(macd_hist[-1]) if not np.isnan(macd_hist[-1]) else 0.0
        sma20_val = float(sma_20[-1]) if not np.isnan(sma_20[-1]) else 0.0
        sma50_val = float(sma_50[-1]) if not np.isnan(sma_50[-1]) else 0.0
        sma200_val = float(sma_200[-1]) if not np.isnan(sma_200[-1]) else 0.0
        bb_upper_val = float(bb_upper[-1]) if not np.isnan(bb_upper[-1]) else 0.0
        bb_middle_val = float(bb_middle[-1]) if not np.isnan(bb_middle[-1]) else 0.0
        bb_lower_val = float(bb_lower[-1]) if not np.isnan(bb_lower[-1]) else 0.0
        vol_val = float(volume[-20:].mean())

        # Trend analysis (values already converted to 0.0 if NaN)
        above_20sma = price_val > sma20_val if sma20_val > 0 else False
        above_50sma = price_val > sma50_val if sma50_val > 0 else False
        above_200sma = price_val > sma200_val if sma200_val > 0 else False
        sma_20_50_bullish = sma20_val > sma50_val if (sma20_val > 0 and sma50_val > 0) else False
        sma_50_200_bullish = sma50_val > sma200_val if (sma50_val > 0 and sma200_val > 0) else False
        macd_bullish = macd_val > macd_sig_val

        # Create analysis text
        analysis_text = f"""
Technical Analysis for {symbol}:

Trend Analysis:
- Above 20 SMA: {'✅' if above_20sma else '❌'}
- Above 50 SMA: {'✅' if above_50sma else '❌'}
- Above 200 SMA: {'✅' if above_200sma else '❌'}
- 20/50 SMA Bullish Cross: {'✅' if sma_20_50_bullish else '❌'}
- 50/200 SMA Bullish Cross: {'✅' if sma_50_200_bullish else '❌'}

Momentum:
- RSI (14): {rsi_val:.2f}
- MACD Bullish: {'✅' if macd_bullish else '❌'}

Latest Price: ${price_val:.2f}
Average True Range (14): {atr_val:.2f}
Average Volume (20D): {vol_val:,.0f}
"""

        # Save as JSON
        output_dir = os.path.join(work_dir, '01_technical')
        os.makedirs(output_dir, exist_ok=True)

        analysis_data = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'latest_price': price_val,
            'indicators': {
                'sma_20': sma20_val if sma20_val > 0 else None,
                'sma_50': sma50_val if sma50_val > 0 else None,
                'sma_200': sma200_val if sma200_val > 0 else None,
                'rsi_14': rsi_val if rsi_val > 0 else None,
                'macd': macd_val,
                'macd_signal': macd_sig_val,
                'macd_histogram': macd_hist_val,
                'atr_14': atr_val if atr_val > 0 else None,
                'bollinger_upper': bb_upper_val if bb_upper_val > 0 else None,
                'bollinger_middle': bb_middle_val if bb_middle_val > 0 else None,
                'bollinger_lower': bb_lower_val if bb_lower_val > 0 else None,
                'avg_volume_20d': vol_val
            },
            'trend_signals': {
                'above_20sma': above_20sma,
                'above_50sma': above_50sma,
                'above_200sma': above_200sma,
                'sma_20_50_bullish': sma_20_50_bullish,
                'sma_50_200_bullish': sma_50_200_bullish,
                'macd_bullish': macd_bullish
            },
            'analysis': analysis_text.strip()
        }

        analysis_path = os.path.join(output_dir, 'technical_analysis.json')
        with open(analysis_path, 'w') as f:
            json.dump(analysis_data, f, indent=2)

        print(f"✓ Saved technical analysis to: {analysis_path}")

        # Print the analysis
        print("\nTechnical Analysis Summary:")
        print("-" * 60)
        print(analysis_text)
        print("-" * 60)

        return True

    except Exception as e:
        print(f"❌ Error in technical analysis: {e}")
        import traceback
        traceback.print_exc()
        return False


def filter_peers_by_industry(symbol, company_name, industry, peers_data):
    """
    Use Claude API to filter peers to only true industry peers.

    Args:
        symbol: Target company ticker
        company_name: Target company name
        industry: Target company industry
        peers_data: Dictionary with 'symbol' and 'name' lists

    Returns:
        tuple: (filtered_peers_data, rationale_text) or (None, None) on error
    """
    try:
        # Import Anthropic here to avoid loading if not needed
        from anthropic import Anthropic

        # Build prompt
        peers_list_text = "\n".join([
            f"- {sym}: {name}"
            for sym, name in zip(peers_data['symbol'], peers_data['name'])
        ])

        # Define structured output schema
        schema = {
            "type": "object",
            "properties": {
                "filtered_peers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string"},
                            "name": {"type": "string"},
                            "keep": {"type": "boolean"},
                            "reason": {"type": "string"}
                        },
                        "required": ["symbol", "name", "keep", "reason"]
                    }
                }
            },
            "required": ["filtered_peers"]
        }

        prompt = f"""I am analyzing {symbol} ({company_name}), which operates in the {industry} industry.

My market data provider gave me this list of potential peer companies:

{peers_list_text}

Please filter this list to include ONLY companies that are:
1. Primarily engaged in the same or closely adjacent industries as {company_name}
2. Comparable in business model and operations

Exclude companies that are:
- In completely different industries
- Vertically integrated suppliers or customers (not peers)

For EACH company in the list above, you must provide:
- symbol: the ticker symbol
- name: the company name
- keep: true if it's a peer, false if not
- reason: brief explanation (one sentence)

You must evaluate ALL {len(peers_data['symbol'])} companies from the list."""

        # Call Claude API with structured output
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            print("⚠ Warning: ANTHROPIC_API_KEY not set, skipping peer filtering")
            return None, None

        client = Anthropic(api_key=api_key)

        try:
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "peer_filter_result",
                        "strict": True,
                        "schema": schema
                    }
                }
            )
        except TypeError:
            # Fallback if response_format not supported in this SDK version
            print("  Note: Using prompt-based JSON (SDK doesn't support response_format)")
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4000,
                system="You are a financial analyst. Respond ONLY with valid JSON matching the requested schema. Do not include any explanatory text, markdown formatting, or code blocks.",
                messages=[{
                    "role": "user",
                    "content": prompt + f"\n\nRespond with JSON matching this schema:\n{json.dumps(schema, indent=2)}"
                }]
            )

        # Parse structured JSON response
        response_text = response.content[0].text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            if lines[0].strip() == '```json':
                response_text = '\n'.join(lines[1:-1])
            else:
                response_text = '\n'.join(lines[1:-1])

        result = json.loads(response_text)

        # Build filtered peers data
        filtered_symbols = []
        filtered_names = []
        filtered_prices = []
        filtered_market_caps = []
        rationale_lines = []

        for peer_decision in result['filtered_peers']:
            symbol_val = peer_decision['symbol']
            name_val = peer_decision['name']
            keep = peer_decision['keep']
            reason = peer_decision['reason']

            # Find index in original data
            try:
                idx = peers_data['symbol'].index(symbol_val)
            except ValueError:
                print(f"⚠ Warning: {symbol_val} not found in original peers data")
                continue

            if keep:
                filtered_symbols.append(peers_data['symbol'][idx])
                filtered_names.append(peers_data['name'][idx])
                if 'price' in peers_data:
                    filtered_prices.append(peers_data['price'][idx])
                if 'market_cap' in peers_data:
                    filtered_market_caps.append(peers_data['market_cap'][idx])
                rationale_lines.append(f"✓ KEEP {symbol_val}: {reason}")
            else:
                rationale_lines.append(f"✗ EXCLUDE {symbol_val}: {reason}")

        # Build filtered peers data structure
        filtered_peers = {
            'symbol': filtered_symbols,
            'name': filtered_names
        }
        if 'price' in peers_data:
            filtered_peers['price'] = filtered_prices
        if 'market_cap' in peers_data:
            filtered_peers['market_cap'] = filtered_market_caps

        rationale_text = "\n".join(rationale_lines)

        return filtered_peers, rationale_text

    except Exception as e:
        print(f"⚠ Warning: Could not filter peers: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def save_peers_list(symbol, work_dir, custom_peers=None, filter_peers=True):
    """
    Get and save peer companies list.

    Args:
        symbol: Stock ticker symbol
        work_dir: Work directory path
        custom_peers: Optional comma-separated custom peer tickers
        filter_peers: If True, use Claude API to filter peers by industry

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Getting peer companies for {symbol}...")

        if custom_peers:
            # Use custom peers provided by user
            peer_symbols = [p.strip().upper() for p in custom_peers.split(',')]
            print(f"✓ Using custom peers: {', '.join(peer_symbols)}")

            # Fetch metadata for each peer using yfinance
            names = []
            prices = []
            market_caps = []

            for peer in peer_symbols:
                try:
                    ticker = yf.Ticker(peer)
                    info = ticker.info
                    names.append(info.get('longName', peer))
                    # Use currentPrice or regularMarketPrice
                    price = info.get('currentPrice') or info.get('regularMarketPrice', 0.0)
                    prices.append(float(price) if price else 0.0)
                    market_caps.append(info.get('marketCap', 0))
                    print(f"  ✓ {peer}: {names[-1]}")
                except Exception as e:
                    print(f"  ⚠ Warning: Could not fetch complete data for {peer}: {e}")
                    names.append(peer)
                    prices.append(0.0)
                    market_caps.append(0)

            # Create peers data structure (same format as OpenBB)
            peers_data = {
                'symbol': peer_symbols,
                'name': names,
                'price': prices,
                'market_cap': market_caps
            }
        else:
            # Auto-detect peers using fallback chain: Finnhub -> OpenBB+FMP
            print(f"Auto-detecting peers for {symbol}...")
            print(f"Fallback chain: Finnhub → OpenBB+FMP\n")

            peers_data, provider_used, all_errors = get_peers_with_fallback(symbol)

            if provider_used == 'none':
                # All providers failed
                print(f"\n⚠ WARNING: Could not auto-detect peers from any provider")
                print(f"\nProvider errors:")
                for provider, error in all_errors.items():
                    if error:
                        print(f"  • {provider}: {error}")
                print(f"\nOptions for future runs:")
                print(f"  1. Provide custom peers: --peers 'SYM1,SYM2,SYM3'")
                print(f"  2. Set FINNHUB_API_KEY in .env (recommended - free tier)")
                print(f"     Get free API key at: https://finnhub.io/register")
                print(f"  3. Set OPENBB_PAT in .env (note: FMP peers requires paid subscription)")
                print(f"\nProceeding with empty peers list...\n")
            else:
                print(f"\n✓ Successfully detected peers using {provider_used}\n")

        # Save to file (same for both paths)
        output_dir = os.path.join(work_dir, '01_technical')
        os.makedirs(output_dir, exist_ok=True)

        peers_path = os.path.join(output_dir, 'peers_list.json')
        with open(peers_path, 'w') as f:
            json.dump(peers_data, f, indent=2)

        print(f"✓ Saved peers list to: {peers_path}")

        # Print peer symbols
        if 'symbol' in peers_data and isinstance(peers_data['symbol'], list):
            peer_symbols_list = peers_data['symbol']
            print(f"✓ Raw peer list ({len(peer_symbols_list)}): {', '.join(peer_symbols_list[:10])}")
        elif 'results' in peers_data and isinstance(peers_data['results'], list):
            peer_symbols_list = [p.get('symbol', 'N/A') for p in peers_data['results']]
            print(f"✓ Found {len(peer_symbols_list)} peers: {', '.join(peer_symbols_list[:10])}")
        elif 'peers_list' in peers_data:
            print(f"✓ Peers: {', '.join(peers_data['peers_list'][:10])}")

        # Apply peer filtering if requested
        if filter_peers:
            print(f"\nFiltering peers using Claude API...")

            # Need company overview for industry classification
            overview_path = os.path.join(work_dir, '02_fundamental', 'company_overview.json')
            if os.path.exists(overview_path):
                with open(overview_path, 'r') as f:
                    overview = json.load(f)

                company_name = overview.get('company_name', symbol)
                industry = overview.get('industry', 'Unknown')

                print(f"Target company: {company_name}")
                print(f"Industry: {industry}")

                # Filter peers
                filtered_peers, rationale = filter_peers_by_industry(
                    symbol, company_name, industry, peers_data
                )

                if filtered_peers:
                    # Save raw peers as backup
                    raw_peers_path = os.path.join(output_dir, 'peers_list_raw.json')
                    with open(raw_peers_path, 'w') as f:
                        json.dump(peers_data, f, indent=2)
                    print(f"✓ Saved raw peers to: {raw_peers_path}")

                    # Replace with filtered peers
                    with open(peers_path, 'w') as f:
                        json.dump(filtered_peers, f, indent=2)
                    print(f"✓ Saved filtered peers to: {peers_path}")

                    # Print rationale
                    print("\nFiltering Results:")
                    print("-" * 60)
                    print(rationale)
                    print("-" * 60)

                    original_count = len(peers_data['symbol']) if 'symbol' in peers_data else 0
                    filtered_count = len(filtered_peers['symbol'])
                    print(f"\n✓ Filtered from {original_count} to {filtered_count} peers")
                    print(f"✓ Final peer list: {', '.join(filtered_peers['symbol'])}")
                else:
                    print("⚠ Peer filtering failed, using raw peer list")
            else:
                print(f"⚠ Warning: Company overview not found at {overview_path}")
                print("  Run research_fundamental.py first, or run without --filter-peers")
                print("  Using raw peer list")

        return True

    except Exception as e:
        print(f"❌ Error getting peers: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Technical analysis research phase'
    )
    parser.add_argument(
        'symbol',
        help='Stock ticker symbol (e.g., INTC, AAPL, MSFT)'
    )
    parser.add_argument(
        '--work-dir',
        default=None,
        help='Work directory path (default: work/SYMBOL_YYYYMMDD)'
    )
    parser.add_argument(
        '--peers',
        default=None,
        help='Comma-separated list of custom peer tickers to override auto-detection'
    )
    parser.add_argument(
        '--no-filter-peers',
        action='store_true',
        help='Disable peer filtering (filtering is enabled by default)'
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
    print("Technical Analysis Phase")
    print("=" * 60)
    print(f"Symbol: {symbol}")
    print(f"Work Directory: {work_dir}")
    print("=" * 60)

    success_count = 0
    total_count = 3

    # Task 1: Generate chart
    if save_chart(symbol, work_dir):
        success_count += 1

    # Task 2: Run technical analysis
    if save_technical_analysis(symbol, work_dir):
        success_count += 1

    # Task 3: Get peers list
    filter_peers = not args.no_filter_peers  # Filter by default unless --no-filter-peers
    if save_peers_list(symbol, work_dir, args.peers, filter_peers):
        success_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("Technical Analysis Phase Complete")
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
