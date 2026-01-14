#!/opt/anaconda3/envs/mcpskills/bin/python3
"""
Final Report Assembly Phase

Combines all research outputs into polished final report with multi-format export.

Usage:
    ./skills/research_final.py SYMBOL [--work-dir DIR]

Output:
    - final_report.md
    - final_report.docx (if pandoc or python-docx available)
    - final_report.html (if pandoc or markdown available)
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import subprocess
import re

# Template engine
from jinja2 import Environment, FileSystemLoader


def load_all_data(work_dir, symbol):
    """
    Load all research data including deep research output.

    Extends the load_data function from research_report.py.

    Args:
        work_dir: Work directory path
        symbol: Stock ticker symbol

    Returns:
        dict: Dictionary containing all research data
    """
    # Start with basic structure
    data = {
        'symbol': symbol,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'company_name': 'N/A',
        'sector': 'N/A',
        'industry': 'N/A',
        'latest_price': 'N/A',
        'market_cap': 'N/A',
    }

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
                    if not pe_row.empty:
                        pe_val = pe_row[peer_symbol].values[0]
                        peer_info['pe_ratio'] = f"{pe_val:.2f}" if pd.notna(pe_val) else 'N/A'
                    else:
                        peer_info['pe_ratio'] = 'N/A'

                    # Revenue
                    rev_row = ratios_df[ratios_df['Metric'] == 'Revenue (ttm)']
                    if not rev_row.empty:
                        rev_val = rev_row[peer_symbol].values[0]
                        if pd.notna(rev_val):
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
                    if not margin_row.empty:
                        margin_val = margin_row[peer_symbol].values[0]
                        if pd.notna(margin_val):
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
                    if not roe_row.empty:
                        roe_val = roe_row[peer_symbol].values[0]
                        if pd.notna(roe_val):
                            try:
                                peer_info['roe'] = f"{float(roe_val)*100:.1f}%"
                            except:
                                peer_info['roe'] = 'N/A'
                        else:
                            peer_info['roe'] = 'N/A'
                    else:
                        peer_info['roe'] = 'N/A'
                else:
                    peer_info['pe_ratio'] = 'N/A'
                    peer_info['revenue'] = 'N/A'
                    peer_info['profit_margin'] = 'N/A'
                    peer_info['roe'] = 'N/A'

                peers.append(peer_info)

            data['peers'] = peers[:10]

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

            if overview.get('market_cap') != 'N/A':
                data['market_cap'] = f"{overview['market_cap']:,.0f}"

            # Financial metrics
            data['revenue'] = f"{overview.get('revenue', 0):,.0f}" if overview.get('revenue') != 'N/A' else 'N/A'

            # Margins
            if overview.get('profit_margin') != 'N/A' and overview.get('profit_margin') is not None:
                data['profit_margin'] = f"{overview['profit_margin']*100:.2f}"
            else:
                data['profit_margin'] = 'N/A'

            # Returns
            if overview.get('roe') != 'N/A' and overview.get('roe') is not None:
                data['roe'] = f"{overview['roe']*100:.2f}"
            else:
                data['roe'] = 'N/A'

            # Valuation
            data['trailing_pe'] = f"{overview.get('trailing_pe', 0):.2f}" if overview.get('trailing_pe') != 'N/A' else 'N/A'

    # Load deep research output
    deep_output_path = os.path.join(work_dir, '08_deep_research/deep_research_output.md')
    if os.path.exists(deep_output_path):
        with open(deep_output_path, 'r') as f:
            deep_content = f.read()
            data['deep_research_output'] = deep_content

            # Try to extract summary and conclusion sections
            # Look for "## 1" or "1." for summary
            summary_match = re.search(r'#+\s*1\.?\s*.*?[Ss]ummary.*?\n+(.*?)(?=\n#+|\Z)', deep_content, re.DOTALL)
            if summary_match:
                data['deep_summary'] = summary_match.group(1).strip()

            # Look for "## 12" or "12." for conclusion
            conclusion_match = re.search(r'#+\s*12\.?\s*.*?[Cc]onclusion.*?\n+(.*?)(?=\n#+|\Z)', deep_content, re.DOTALL)
            if conclusion_match:
                data['deep_conclusion'] = conclusion_match.group(1).strip()
    else:
        data['deep_research_output'] = '*Deep research not yet completed.*'

    return data


def generate_final_report(data, work_dir):
    """Generate final report using template."""
    # Setup Jinja2 environment
    template_dir = 'templates'
    env = Environment(loader=FileSystemLoader(template_dir))

    # Custom filter for number formatting
    def format_number(value):
        try:
            return f"{int(value):,}"
        except:
            return value

    env.filters['format_number'] = format_number

    # Load template
    template = env.get_template('final_report.md.j2')

    # Render template
    report_content = template.render(**data)
    report_content = report_content.replace('$', '\\$')

    # Save markdown file
    report_path = os.path.join(work_dir, 'final_report.md')
    with open(report_path, 'w') as f:
        f.write(report_content)

    print(f"✓ Saved: {report_path}")
    return report_path


def convert_to_docx(md_path, docx_path):
    """Convert markdown to Word document using pandoc or python-docx."""
    try:
        # Try pandoc first (most reliable)
        result = subprocess.run(
            ['pandoc', md_path, '-o', docx_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print(f"✓ Saved: {docx_path} (via pandoc)")
            return True
        else:
            print(f"⚠ Pandoc conversion failed: {result.stderr}")

    except FileNotFoundError:
        print("⚠ Pandoc not found. Install with: brew install pandoc")
    except Exception as e:
        print(f"⚠ Pandoc error: {e}")

    # Try python-docx as fallback
    try:
        from docx import Document
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        # Read markdown content
        with open(md_path, 'r') as f:
            content = f.read()

        # Simple markdown to docx conversion
        for line in content.split('\n'):
            if line.startswith('# '):
                # Heading 1
                p = doc.add_heading(line[2:], level=1)
            elif line.startswith('## '):
                # Heading 2
                p = doc.add_heading(line[3:], level=2)
            elif line.startswith('### '):
                # Heading 3
                p = doc.add_heading(line[4:], level=3)
            elif line.strip() == '---':
                # Horizontal rule (skip)
                continue
            elif line.startswith('| '):
                # Table row (simplified handling)
                p = doc.add_paragraph(line)
                p.style = 'Normal'
            elif line.startswith('**') and line.endswith('**'):
                # Bold text
                p = doc.add_paragraph(line.strip('**'))
                p.runs[0].bold = True
            else:
                # Regular paragraph
                if line.strip():
                    doc.add_paragraph(line)

        doc.save(docx_path)
        print(f"✓ Saved: {docx_path} (via python-docx)")
        return True

    except ImportError:
        print("⚠ python-docx not found. Install with: pip install python-docx")
    except Exception as e:
        print(f"⚠ python-docx error: {e}")

    return False


def convert_to_html(md_path, html_path):
    """Convert markdown to HTML using pandoc or markdown library."""
    try:
        # Try pandoc first (most reliable)
        result = subprocess.run(
            ['pandoc', md_path, '-o', html_path, '--standalone', '--toc', '--css', 'style.css'],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print(f"✓ Saved: {html_path} (via pandoc)")
            return True
        else:
            print(f"⚠ Pandoc conversion failed: {result.stderr}")

    except FileNotFoundError:
        print("⚠ Pandoc not found for HTML conversion")
    except Exception as e:
        print(f"⚠ Pandoc error: {e}")

    # Try markdown library as fallback
    try:
        import markdown

        with open(md_path, 'r') as f:
            md_content = f.read()

        # Convert markdown to HTML with extensions
        html_content = markdown.markdown(
            md_content,
            extensions=['tables', 'fenced_code', 'toc', 'meta']
        )

        # Wrap in basic HTML template with styling
        full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Equity Research Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 30px 0;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""

        with open(html_path, 'w') as f:
            f.write(full_html)

        print(f"✓ Saved: {html_path} (via markdown library)")
        return True

    except ImportError:
        print("⚠ markdown library not found. Install with: pip install markdown")
    except Exception as e:
        print(f"⚠ markdown library error: {e}")

    return False


def main():
    parser = argparse.ArgumentParser(description='Final report assembly phase')
    parser.add_argument('symbol', help='Stock ticker symbol')
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

    print("="*60)
    print("Final Report Assembly Phase")
    print("="*60)
    print(f"Symbol: {symbol}")
    print(f"Work Directory: {work_dir}")
    print("="*60)

    try:
        # Load all data
        print(f"\nLoading all research data...")
        data = load_all_data(work_dir, symbol)
        print(f"✓ Data loaded")

        # Generate final report
        print(f"\nGenerating final report...")
        md_path = generate_final_report(data, work_dir)

        # Convert to other formats
        print(f"\nConverting to additional formats...")

        # DOCX
        docx_path = os.path.join(work_dir, 'final_report.docx')
        convert_to_docx(md_path, docx_path)

        # HTML
        html_path = os.path.join(work_dir, 'final_report.html')
        convert_to_html(md_path, html_path)

        print("\n" + "="*60)
        print("SUCCESS: Final report assembly completed!")
        print("="*60)
        print(f"\nOutputs:")
        print(f"  - {md_path}")
        if os.path.exists(docx_path):
            print(f"  - {docx_path}")
        if os.path.exists(html_path):
            print(f"  - {html_path}")

        return 0

    except Exception as e:
        print(f"\n❌ Error in final report assembly: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
