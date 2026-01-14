#!/opt/anaconda3/envs/mcpskills/bin/python3
"""
Report Generation Phase

Generates comprehensive analyst-style report from all research phases.

Usage:
    ./skills/research_report.py SYMBOL [--work-dir DIR]

    If --work-dir is not specified, creates work/SYMBOL_YYYYMMDD automatically.

Examples:
    ./skills/research_report.py TSLA
    ./skills/research_report.py AAPL --work-dir custom/directory

Output:
    - research_report.md - Markdown report
    - research_report.html - HTML report (optional)
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path
import pandas as pd

# Template engine
from jinja2 import Environment, FileSystemLoader


def load_data(work_dir, symbol):
    """
    Load all research data from phase outputs.

    Args:
        work_dir: Work directory path
        symbol: Stock ticker symbol

    Returns:
        dict: Dictionary containing all research data
    """
    data = {
        'symbol': symbol,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'company_name': 'N/A',
        'sector': 'N/A',
        'industry': 'N/A',
        'latest_price': 'N/A',
        'market_cap': 'N/A',
    }

    # Load metadata (optional - symbol already set from parameter)
    metadata_path = os.path.join(work_dir, '00_metadata.json')
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
            # Metadata can override if present, but not required
            if metadata.get('symbol'):
                data['symbol'] = metadata.get('symbol')

    # Load technical analysis
    tech_path = os.path.join(work_dir, '01_technical/technical_analysis.json')
    if os.path.exists(tech_path):
        with open(tech_path, 'r') as f:
            data['technical_analysis'] = json.load(f)
            if 'latest_price' in data['technical_analysis']:
                data['latest_price'] = f"{data['technical_analysis']['latest_price']:.2f}"

    # Load peers list with enhanced metrics
    peers_path = os.path.join(work_dir, '01_technical/peers_list.json')
    ratios_path = os.path.join(work_dir, '02_fundamental/key_ratios.csv')

    if os.path.exists(peers_path):
        with open(peers_path, 'r') as f:
            peers_data = json.load(f)

        # Load key ratios for peer metrics
        ratios_df = None
        if os.path.exists(ratios_path):
            ratios_df = pd.read_csv(ratios_path)

        # Convert to list of dicts with enhanced metrics
        if 'symbol' in peers_data and isinstance(peers_data['symbol'], list):
            peers = []
            for i, peer_symbol in enumerate(peers_data['symbol']):
                peer_info = {
                    'symbol': peer_symbol,
                    'name': peers_data.get('name', [])[i] if i < len(peers_data.get('name', [])) else 'N/A',
                    'price': f"{peers_data.get('price', [])[i]:.2f}" if i < len(peers_data.get('price', [])) and peers_data.get('price', [])[i] else 'N/A',
                    'market_cap': f"{peers_data.get('market_cap', [])[i]:,.0f}" if i < len(peers_data.get('market_cap', [])) and peers_data.get('market_cap', [])[i] else 'N/A',
                }

                # Add financial metrics from ratios_df if available
                if ratios_df is not None and peer_symbol in ratios_df.columns:
                    # P/E Ratio
                    pe_row = ratios_df[ratios_df['Metric'] == 'Trailing P/E']
                    if not pe_row.empty and peer_symbol in pe_row.columns:
                        pe_val = pe_row[peer_symbol].values[0]
                        peer_info['pe_ratio'] = f"{pe_val:.2f}" if pd.notna(pe_val) and pe_val != 'N/A' else 'N/A'
                    else:
                        peer_info['pe_ratio'] = 'N/A'

                    # Revenue (TTM)
                    rev_row = ratios_df[ratios_df['Metric'] == 'Revenue (ttm)']
                    if not rev_row.empty and peer_symbol in rev_row.columns:
                        rev_val = rev_row[peer_symbol].values[0]
                        if pd.notna(rev_val) and rev_val != 'N/A':
                            try:
                                peer_info['revenue'] = f"${float(rev_val)/1e9:.1f}B"
                            except:
                                peer_info['revenue'] = 'N/A'
                        else:
                            peer_info['revenue'] = 'N/A'
                    else:
                        peer_info['revenue'] = 'N/A'

                    # Profit Margin
                    margin_row = ratios_df[ratios_df['Metric'] == 'Profit Margin']
                    if not margin_row.empty and peer_symbol in margin_row.columns:
                        margin_val = margin_row[peer_symbol].values[0]
                        if pd.notna(margin_val) and margin_val != 'N/A':
                            try:
                                peer_info['profit_margin'] = f"{float(margin_val)*100:.1f}%"
                            except:
                                peer_info['profit_margin'] = 'N/A'
                        else:
                            peer_info['profit_margin'] = 'N/A'
                    else:
                        peer_info['profit_margin'] = 'N/A'

                    # ROE
                    roe_row = ratios_df[ratios_df['Metric'] == 'Return on Equity']
                    if not roe_row.empty and peer_symbol in roe_row.columns:
                        roe_val = roe_row[peer_symbol].values[0]
                        if pd.notna(roe_val) and roe_val != 'N/A':
                            try:
                                peer_info['roe'] = f"{float(roe_val)*100:.1f}%"
                            except:
                                peer_info['roe'] = 'N/A'
                        else:
                            peer_info['roe'] = 'N/A'
                    else:
                        peer_info['roe'] = 'N/A'
                else:
                    # No ratios data available
                    peer_info['pe_ratio'] = 'N/A'
                    peer_info['revenue'] = 'N/A'
                    peer_info['profit_margin'] = 'N/A'
                    peer_info['roe'] = 'N/A'

                peers.append(peer_info)

            data['peers'] = peers[:10]  # Limit to top 10

    # Check for chart
    chart_path = os.path.join(work_dir, '01_technical/chart.png')
    if os.path.exists(chart_path):
        data['chart_path'] = '01_technical/chart.png'

    # Check for income statement Sankey chart
    sankey_path = os.path.join(work_dir, '02_fundamental/income_statement_sankey.png')
    if os.path.exists(sankey_path):
        data['income_statement_sankey_path'] = '02_fundamental/income_statement_sankey.png'

    # Load fundamental data
    overview_path = os.path.join(work_dir, '02_fundamental/company_overview.json')
    if os.path.exists(overview_path):
        with open(overview_path, 'r') as f:
            overview = json.load(f)
            data['company_name'] = overview.get('company_name', 'N/A')
            data['sector'] = overview.get('sector', 'N/A')
            data['industry'] = overview.get('industry', 'N/A')
            data['business_summary'] = overview.get('business_summary', '')

            if overview.get('market_cap') != 'N/A':
                data['market_cap'] = f"{overview['market_cap']:,.0f}"

            # Financial metrics
            data['revenue'] = f"{overview.get('revenue', 0):,.0f}" if overview.get('revenue') != 'N/A' else 'N/A'
            data['revenue_per_share'] = f"{overview.get('revenue_per_share', 0):.2f}" if overview.get('revenue_per_share') != 'N/A' else 'N/A'

            if overview.get('quarterly_revenue_growth') != 'N/A' and overview.get('quarterly_revenue_growth') is not None:
                data['quarterly_revenue_growth'] = f"{overview['quarterly_revenue_growth']*100:.2f}"

            data['gross_profit'] = f"{overview.get('gross_profit', 0):,.0f}" if overview.get('gross_profit') != 'N/A' else 'N/A'
            data['ebitda'] = f"{overview.get('ebitda', 0):,.0f}" if overview.get('ebitda') != 'N/A' else 'N/A'

            # Margins
            if overview.get('profit_margin') != 'N/A' and overview.get('profit_margin') is not None:
                data['profit_margin'] = f"{overview['profit_margin']*100:.2f}"
            if overview.get('operating_margin') != 'N/A' and overview.get('operating_margin') is not None:
                data['operating_margin'] = f"{overview['operating_margin']*100:.2f}"

            # Returns
            if overview.get('roe') != 'N/A' and overview.get('roe') is not None:
                data['roe'] = f"{overview['roe']*100:.2f}"
            if overview.get('roa') != 'N/A' and overview.get('roa') is not None:
                data['roa'] = f"{overview['roa']*100:.2f}"

            # Valuation
            data['trailing_pe'] = f"{overview.get('trailing_pe', 0):.2f}" if overview.get('trailing_pe') != 'N/A' else 'N/A'
            data['forward_pe'] = f"{overview.get('forward_pe', 0):.2f}" if overview.get('forward_pe') != 'N/A' else 'N/A'
            data['peg_ratio'] = f"{overview.get('peg_ratio', 0):.2f}" if overview.get('peg_ratio') != 'N/A' else 'N/A'
            data['price_to_book'] = f"{overview.get('price_to_book', 0):.2f}" if overview.get('price_to_book') != 'N/A' else 'N/A'
            data['price_to_sales'] = f"{overview.get('price_to_sales', 0):.2f}" if overview.get('price_to_sales') != 'N/A' else 'N/A'

    # Load analyst recommendations
    recs_path = os.path.join(work_dir, '02_fundamental/analyst_recommendations.json')
    if os.path.exists(recs_path):
        with open(recs_path, 'r') as f:
            recs = json.load(f)
            # Convert to DataFrame-like format for template
            data['analyst_recommendations'] = recs

    # Load Perplexity research
    news_path = os.path.join(work_dir, '03_research/news_stories.md')
    if os.path.exists(news_path):
        with open(news_path, 'r') as f:
            data['news_stories'] = f.read()

    business_profile_path = os.path.join(work_dir, '03_research/business_profile.md')
    if os.path.exists(business_profile_path):
        with open(business_profile_path, 'r') as f:
            data['business_profile'] = f.read()

    exec_profiles_path = os.path.join(work_dir, '03_research/executive_profiles.md')
    if os.path.exists(exec_profiles_path):
        with open(exec_profiles_path, 'r') as f:
            data['executive_profiles'] = f.read()

    # Load SEC data
    sec_metadata_path = os.path.join(work_dir, '04_sec/10k_metadata.json')
    if os.path.exists(sec_metadata_path):
        with open(sec_metadata_path, 'r') as f:
            sec_data = json.load(f)
            data['sec_filing_url'] = sec_data.get('filing_url', '')
            data['sec_filing_date'] = sec_data.get('filing_date', '')
            data['sec_report_date'] = sec_data.get('report_date', '')

    # Load Wikipedia data
    wiki_summary_path = os.path.join(work_dir, '05_wikipedia/wikipedia_summary.txt')
    if os.path.exists(wiki_summary_path):
        with open(wiki_summary_path, 'r') as f:
            wiki_text = f.read()
            # Extract just the summary part (after the header)
            lines = wiki_text.split('\n')
            summary_start = False
            summary_lines = []
            for line in lines:
                if '=' * 60 in line:
                    if summary_start:
                        break
                    summary_start = True
                    continue
                if summary_start and line.strip():
                    summary_lines.append(line)
            data['wikipedia_summary'] = '\n'.join(summary_lines)

    # Load deep analysis data
    analysis_dir = os.path.join(work_dir, '06_analysis')

    # Business model analysis
    business_model_path = os.path.join(analysis_dir, 'business_model_analysis.md')
    if os.path.exists(business_model_path):
        with open(business_model_path, 'r') as f:
            data['business_model_analysis'] = f.read()

    # Competitive analysis
    competitive_path = os.path.join(analysis_dir, 'competitive_analysis.md')
    if os.path.exists(competitive_path):
        with open(competitive_path, 'r') as f:
            data['competitive_analysis'] = f.read()

    # Supply chain analysis
    supply_chain_path = os.path.join(analysis_dir, 'supply_chain_analysis.md')
    if os.path.exists(supply_chain_path):
        with open(supply_chain_path, 'r') as f:
            data['supply_chain_analysis'] = f.read()

    # Risk analysis
    risk_analysis_path = os.path.join(analysis_dir, 'risk_analysis.md')
    if os.path.exists(risk_analysis_path):
        with open(risk_analysis_path, 'r') as f:
            data['recent_news_analysis'] = f.read()

    # Investment thesis
    thesis_path = os.path.join(analysis_dir, 'investment_thesis.md')
    if os.path.exists(thesis_path):
        with open(thesis_path, 'r') as f:
            thesis_content = f.read()
            data['investment_thesis'] = thesis_content

            # Try to extract specific sections from investment thesis
            # This is a simple approach - could be enhanced with better parsing
            if 'Bull Case' in thesis_content or 'bull case' in thesis_content.lower():
                # Extract bull case section
                import re
                bull_match = re.search(r'(?:Bull Case|BULL CASE)[\s\S]*?(?=(?:Bear Case|BEAR CASE|Base Case|##|$))', thesis_content, re.IGNORECASE)
                if bull_match:
                    data['bull_case'] = bull_match.group(0).strip()

            if 'Bear Case' in thesis_content or 'bear case' in thesis_content.lower():
                # Extract bear case section
                bear_match = re.search(r'(?:Bear Case|BEAR CASE)[\s\S]*?(?=(?:Base Case|BASE CASE|Critical Watch|##|$))', thesis_content, re.IGNORECASE)
                if bear_match:
                    data['bear_case'] = bear_match.group(0).strip()

            if 'SWOT' in thesis_content:
                # Extract SWOT sections
                strengths_match = re.search(r'(?:Strengths|STRENGTHS)[\s\S]*?(?=(?:Weaknesses|WEAKNESSES|##))', thesis_content, re.IGNORECASE)
                if strengths_match:
                    data['strengths'] = strengths_match.group(0).strip()

                weaknesses_match = re.search(r'(?:Weaknesses|WEAKNESSES)[\s\S]*?(?=(?:Opportunities|OPPORTUNITIES|##))', thesis_content, re.IGNORECASE)
                if weaknesses_match:
                    data['weaknesses'] = weaknesses_match.group(0).strip()

                opportunities_match = re.search(r'(?:Opportunities|OPPORTUNITIES)[\s\S]*?(?=(?:Threats|THREATS|##))', thesis_content, re.IGNORECASE)
                if opportunities_match:
                    data['opportunities'] = opportunities_match.group(0).strip()

                threats_match = re.search(r'(?:Threats|THREATS)[\s\S]*?(?=(?:Bull Case|BULL CASE|##|$))', thesis_content, re.IGNORECASE)
                if threats_match:
                    data['threats'] = threats_match.group(0).strip()

    # Load SEC 10-K Item 1 excerpt (first 5000 chars for supply chain info)
    item1_path = os.path.join(work_dir, '04_sec/10k_item1.txt')
    if os.path.exists(item1_path):
        with open(item1_path, 'r', encoding='utf-8', errors='ignore') as f:
            item1_text = f.read()
            # Extract a reasonable excerpt for business description
            if len(item1_text) > 5000:
                data['sec_item1_business'] = item1_text[:5000] + "\n\n[...continued in full 10-K filing]"
            else:
                data['sec_item1_business'] = item1_text

    # Reference file paths for detailed analysis
    balance_sheet_path = os.path.join(work_dir, '02_fundamental/balance_sheet.csv')
    if os.path.exists(balance_sheet_path):
        data['balance_sheet_file'] = balance_sheet_path

    cash_flow_path = os.path.join(work_dir, '02_fundamental/cash_flow.csv')
    if os.path.exists(cash_flow_path):
        data['cash_flow_file'] = cash_flow_path

    return data


def generate_report(work_dir, symbol, output_format='markdown', template_name='equity_research_report.md.j2'):
    """
    Generate the research report.

    Args:
        work_dir: Work directory path
        symbol: Stock ticker symbol
        output_format: 'markdown' or 'html'
        template_name: Template file to use

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Generating {output_format} report...")
        print(f"  Using template: {template_name}")

        # Load all data
        data = load_data(work_dir, symbol)

        if not data['symbol']:
            print("❌ Could not determine symbol")
            return False

        print(f"  Symbol: {data['symbol']}")
        print(f"  Company: {data['company_name']}")

        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        env = Environment(loader=FileSystemLoader(template_dir))

        # Add custom filters for formatting
        def format_number(value):
            """Format large numbers with commas."""
            try:
                return f"{int(value):,}"
            except:
                return value
        env.filters['format_number'] = format_number

        # Load template
        template = env.get_template(template_name)

        # Render template
        report_content = template.render(**data)

        # Save markdown report
        report_path = os.path.join(work_dir, 'research_report.md')
        with open(report_path, 'w') as f:
            f.write(report_content)

        print(f"✓ Saved report to: {report_path}")

        # Optionally convert to HTML
        if output_format == 'html':
            try:
                import markdown
                html_content = markdown.markdown(report_content)

                html_path = os.path.join(work_dir, 'research_report.html')
                with open(html_path, 'w') as f:
                    f.write(f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Stock Research Report: {data['symbol']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        img {{ max-width: 100%; height: auto; }}
        hr {{ margin: 30px 0; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>
""")

                print(f"✓ Saved HTML report to: {html_path}")
            except ImportError:
                print("⊘ markdown library not installed, skipping HTML generation")

        return True

    except Exception as e:
        print(f"❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Report generation phase'
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
    parser.add_argument(
        '--format',
        default='markdown',
        choices=['markdown', 'html'],
        help='Output format (default: markdown)'
    )
    parser.add_argument(
        '--template',
        default='equity_research_report.md.j2',
        help='Template file to use (default: equity_research_report.md.j2)'
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
    print("Report Generation Phase")
    print("=" * 60)
    print(f"Symbol: {symbol}")
    print(f"Work Directory: {work_dir}")
    print(f"Format: {args.format}")
    print(f"Template: {args.template}")
    print("=" * 60)

    success = generate_report(work_dir, symbol, args.format, args.template)

    # Summary
    print("\n" + "=" * 60)
    print("Report Generation Phase Complete")
    print("=" * 60)

    if success:
        print("✓ Report generated successfully")
        return 0
    else:
        print("❌ Report generation failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
