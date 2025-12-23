#!/opt/anaconda3/envs/fidelity/bin/python3
"""
Deep Analysis Research Phase

Performs deep analytical research using Perplexity AI for equity research report.

Usage:
    ./skills/research_analysis.py SYMBOL [--work-dir DIR]

    If --work-dir is not specified, creates work/SYMBOL_YYYYMMDD automatically.

Examples:
    ./skills/research_analysis.py TSLA
    ./skills/research_analysis.py AAPL --work-dir custom/directory

Output:
    - Creates 06_analysis/ directory in work directory
    - business_model_analysis.md - Deep dive on business model
    - competitive_analysis.md - Competitive landscape analysis
    - supply_chain_analysis.md - Supply chain positioning
    - valuation_analysis.md - Valuation methodologies and metrics
    - risk_analysis.md - Recent news, investigations, and risk factors
    - investment_thesis.md - Bull/bear cases and SWOT
"""

import os
import sys
import argparse
import time
import json
from datetime import datetime
from pathlib import Path

# Load environment for API keys
from dotenv import load_dotenv
load_dotenv()

# Perplexity API (OpenAI-compatible)
from openai import OpenAI

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


def query_perplexity(prompt, model="sonar-pro", temperature=0.2, max_tokens=4000, max_retries=3):
    """
    Query Perplexity AI with retry logic.

    Args:
        prompt: Query prompt
        model: Perplexity model to use
        temperature: Temperature for response (0.2 for factual)
        max_tokens: Maximum tokens in response
        max_retries: Maximum retry attempts

    Returns:
        str: Response text or None if failed
    """
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        print("❌ ERROR: PERPLEXITY_API_KEY not found in environment")
        return None

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.perplexity.ai"
    )

    for attempt in range(max_retries):
        try:
            print(f"  Querying Perplexity (attempt {attempt + 1}/{max_retries})...")

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an equity research analyst. Provide detailed, well-sourced analysis with specific data points and citations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            result = response.choices[0].message.content
            print(f"  ✓ Received response ({len(result)} characters)")
            return result

        except Exception as e:
            print(f"  ⚠ Attempt {attempt + 1} failed: {e}")

            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 5
                print(f"  Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                print(f"  ❌ All retry attempts failed")
                return None

    return None


def analyze_business_model(symbol, work_dir, company_identifier=None):
    """Deep analysis of business model."""
    try:
        identifier = company_identifier or symbol
        print(f"Analyzing business model for {identifier}...")

        prompt = f"""
Provide a comprehensive business model analysis for {identifier}:

1. **Core Business & Products/Services:**
   - Describe their main products, services, and business lines
   - Explain how they create and deliver value

2. **Revenue Streams:**
   - Break down revenue by product/service category if possible
   - Identify recurring vs one-time revenue
   - Note geographic revenue distribution

3. **Customer Segments & Monetization:**
   - Who are their customers (B2B, B2C, etc.)?
   - How do they acquire customers?
   - What are typical customer acquisition costs (CAC) if known?
   - Customer retention metrics (churn rate, lifetime value)

4. **Market Characteristics:**
   - Sales cycle length
   - Seasonal or cyclical patterns
   - Market size and growth trajectory
   - Key factors affecting margins

5. **Competitive Advantages:**
   - Network effects
   - Switching costs
   - Brand strength
   - Intellectual property/patents
   - Regulatory moats
   - Other barriers to entry

Provide specific numbers, metrics, and data points with citations.
"""

        result = query_perplexity(prompt, max_tokens=6000)

        if result:
            output_dir = os.path.join(work_dir, '04_analysis')
            os.makedirs(output_dir, exist_ok=True)

            output_path = os.path.join(output_dir, 'business_model_analysis.md')
            with open(output_path, 'w') as f:
                f.write(f"# Business Model Analysis - {symbol}\n\n")
                f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write(result)

            print(f"✓ Saved business model analysis to: {output_path}")
            return True
        else:
            print(f"❌ Failed to get business model analysis")
            return False

    except Exception as e:
        print(f"❌ Error in business model analysis: {e}")
        import traceback
        traceback.print_exc()
        return False


def analyze_competitive_landscape(symbol, work_dir, company_identifier=None):
    """Deep analysis of competitive landscape."""
    try:
        identifier = company_identifier or symbol
        print(f"Analyzing competitive landscape for {identifier}...")

        prompt = f"""
Provide a detailed competitive landscape analysis for {identifier}:

1. **Main Competitors:**
   - Direct competitors (same products/markets)
   - Adjacent competitors (substitute products)
   - Emerging competitors (new entrants, disruptors)

2. **Competitive Comparison:**
   - Market share data
   - Product differentiation and positioning
   - Pricing power
   - Growth trajectories
   - Customer satisfaction/NPS scores if available

3. **Competitive Dynamics:**
   - How has competitive landscape changed recently?
   - Who is gaining/losing share?
   - Any major competitive threats or opportunities?

Provide specific data, metrics, and recent developments with citations.
"""

        result = query_perplexity(prompt, max_tokens=5000)

        if result:
            output_dir = os.path.join(work_dir, '04_analysis')
            os.makedirs(output_dir, exist_ok=True)

            output_path = os.path.join(output_dir, 'competitive_analysis.md')
            with open(output_path, 'w') as f:
                f.write(f"# Competitive Landscape Analysis - {symbol}\n\n")
                f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write(result)

            print(f"✓ Saved competitive analysis to: {output_path}")
            return True
        else:
            print(f"❌ Failed to get competitive analysis")
            return False

    except Exception as e:
        print(f"❌ Error in competitive analysis: {e}")
        import traceback
        traceback.print_exc()
        return False


def analyze_risks_and_news(symbol, work_dir, company_identifier=None):
    """Deep analysis of recent news, risks, and investigations."""
    try:
        identifier = company_identifier or symbol
        print(f"Analyzing recent news and risks for {identifier}...")

        prompt = f"""
Conduct a comprehensive news and risk analysis for {identifier} covering the last 12 months:

1. **Analyst Reports & Rating Changes:**
   Search for: {identifier} + "analyst report" OR "research note" OR "downgrade" OR "upgrade"
   Summarize recent analyst actions with firm names and dates

2. **Investigative Reports:**
   Search for: {identifier} + "investigative report" OR "deep dive" OR "short seller"
   Note any critical investigative journalism or short-seller reports

3. **Executive & Governance:**
   - Management changes (C-suite, board)
   - Insider trading activity (significant buys/sells)
   - Executive compensation controversies
   - Governance issues

4. **Operational Developments:**
   - Product launches or failures
   - Restructurings or layoffs
   - M&A activity (acquisitions, divestitures, partnerships)
   - Supply chain disruptions

5. **Legal & Regulatory:**
   - Lawsuits or settlements
   - Regulatory investigations
   - Compliance issues

6. **Financial Performance:**
   - Earnings beats/misses
   - Guidance changes
   - Unexpected financial developments

Provide specific dates, sources, and quantitative impacts where available.
"""

        result = query_perplexity(prompt, max_tokens=8000)

        if result:
            output_dir = os.path.join(work_dir, '04_analysis')
            os.makedirs(output_dir, exist_ok=True)

            output_path = os.path.join(output_dir, 'risk_analysis.md')
            with open(output_path, 'w') as f:
                f.write(f"# Recent News & Risk Analysis - {symbol}\n\n")
                f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write(result)

            print(f"✓ Saved risk analysis to: {output_path}")
            return True
        else:
            print(f"❌ Failed to get risk analysis")
            return False

    except Exception as e:
        print(f"❌ Error in risk analysis: {e}")
        import traceback
        traceback.print_exc()
        return False


def analyze_investment_thesis(symbol, work_dir, company_identifier=None):
    """Generate investment thesis with bull/bear cases and SWOT."""
    try:
        identifier = company_identifier or symbol
        print(f"Generating investment thesis for {identifier}...")

        prompt = f"""
Provide a comprehensive investment thesis for {identifier}:

1. **SWOT Analysis:**
   - Strengths (internal competitive advantages)
   - Weaknesses (internal vulnerabilities)
   - Opportunities (external favorable trends)
   - Threats (external risks)

2. **Bull Case:**
   - Best-case scenario assumptions
   - Key catalysts that could drive outperformance
   - Upside potential quantified if possible

3. **Bear Case:**
   - Worst-case scenario assumptions
   - Key risks that could lead to underperformance
   - Downside risk quantified if possible

4. **Base Case & Risk/Reward:**
   - Most likely scenario
   - Risk/reward profile assessment
   - Overall risk level (low/medium/high)

5. **Critical Watch Points:**
   - Key metrics to monitor
   - Upcoming catalysts or events
   - Warning signs to watch for

Be specific with scenarios and potential outcomes.
"""

        result = query_perplexity(prompt, max_tokens=6000)

        if result:
            output_dir = os.path.join(work_dir, '04_analysis')
            os.makedirs(output_dir, exist_ok=True)

            output_path = os.path.join(output_dir, 'investment_thesis.md')
            with open(output_path, 'w') as f:
                f.write(f"# Investment Thesis - {symbol}\n\n")
                f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write(result)

            print(f"✓ Saved investment thesis to: {output_path}")
            return True
        else:
            print(f"❌ Failed to get investment thesis")
            return False

    except Exception as e:
        print(f"❌ Error in investment thesis: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Deep analysis research phase'
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

    # Get company name for better queries
    company_name = get_company_name(symbol, work_dir)
    company_identifier = f"{company_name} ({symbol})" if company_name != symbol else symbol

    print("=" * 60)
    print("Deep Analysis Research Phase")
    print("=" * 60)
    print(f"Symbol: {symbol}")
    print(f"Company: {company_identifier}")
    print(f"Work Directory: {work_dir}")
    print("=" * 60)

    success_count = 0
    total_count = 4

    # Task 1: Business model analysis
    if analyze_business_model(symbol, work_dir, company_identifier):
        success_count += 1

    # Task 2: Competitive landscape
    if analyze_competitive_landscape(symbol, work_dir, company_identifier):
        success_count += 1

    # Task 3: Recent news and risks
    if analyze_risks_and_news(symbol, work_dir, company_identifier):
        success_count += 1

    # Task 4: Investment thesis
    if analyze_investment_thesis(symbol, work_dir, company_identifier):
        success_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("Deep Analysis Phase Complete")
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
