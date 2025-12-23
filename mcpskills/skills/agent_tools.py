#!/opt/anaconda3/envs/fidelity/bin/python3
"""
Agent Tools for Stock Research

Provides data loading functions that agents can use to access
research data from the work directory.

These functions are designed to be simple, focused tools that
agents can call to retrieve specific pieces of information.
"""

import os
import json
import csv
from typing import Dict, List, Any, Optional


def read_technical_analysis(work_dir: str) -> Dict[str, Any]:
    """
    Load technical analysis data including indicators and trend signals.

    Args:
        work_dir: Path to work directory

    Returns:
        dict: Technical analysis data with indicators and signals
    """
    try:
        with open(f'{work_dir}/01_technical/technical_analysis.json') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "Technical analysis data not found"}
    except Exception as e:
        return {"error": f"Failed to load technical analysis: {str(e)}"}


def read_fundamentals(work_dir: str) -> Dict[str, Any]:
    """
    Load fundamental company data from overview file.

    Args:
        work_dir: Path to work directory

    Returns:
        dict: Company overview with financial metrics
    """
    try:
        with open(f'{work_dir}/02_fundamental/company_overview.json') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "Fundamental data not found"}
    except Exception as e:
        return {"error": f"Failed to load fundamentals: {str(e)}"}


def read_income_statement(work_dir: str) -> List[Dict[str, Any]]:
    """
    Load income statement data.

    Args:
        work_dir: Path to work directory

    Returns:
        list: Income statement data by period
    """
    try:
        with open(f'{work_dir}/02_fundamental/income_statement.csv') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        return [{"error": "Income statement not found"}]
    except Exception as e:
        return [{"error": f"Failed to load income statement: {str(e)}"}]


def read_balance_sheet(work_dir: str) -> List[Dict[str, Any]]:
    """
    Load balance sheet data.

    Args:
        work_dir: Path to work directory

    Returns:
        list: Balance sheet data by period
    """
    try:
        with open(f'{work_dir}/02_fundamental/balance_sheet.csv') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        return [{"error": "Balance sheet not found"}]
    except Exception as e:
        return [{"error": f"Failed to load balance sheet: {str(e)}"}]


def read_cash_flow(work_dir: str) -> List[Dict[str, Any]]:
    """
    Load cash flow statement data.

    Args:
        work_dir: Path to work directory

    Returns:
        list: Cash flow data by period
    """
    try:
        with open(f'{work_dir}/02_fundamental/cash_flow.csv') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        return [{"error": "Cash flow data not found"}]
    except Exception as e:
        return [{"error": f"Failed to load cash flow: {str(e)}"}]


def read_key_ratios(work_dir: str) -> List[Dict[str, Any]]:
    """
    Load financial ratios data.

    Args:
        work_dir: Path to work directory

    Returns:
        list: Financial ratios data
    """
    try:
        with open(f'{work_dir}/02_fundamental/key_ratios.csv') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        return [{"error": "Key ratios not found"}]
    except Exception as e:
        return [{"error": f"Failed to load key ratios: {str(e)}"}]


def read_analyst_recommendations(work_dir: str) -> List[Dict[str, Any]]:
    """
    Load analyst recommendations.

    Args:
        work_dir: Path to work directory

    Returns:
        list: Analyst recommendations with firms and ratings
    """
    try:
        with open(f'{work_dir}/02_fundamental/analyst_recommendations.json') as f:
            return json.load(f)
    except FileNotFoundError:
        return [{"error": "Analyst recommendations not found"}]
    except Exception as e:
        return [{"error": f"Failed to load analyst recommendations: {str(e)}"}]


def read_news_stories(work_dir: str) -> str:
    """
    Load news stories from Perplexity research.

    Args:
        work_dir: Path to work directory

    Returns:
        str: News stories markdown content
    """
    try:
        with open(f'{work_dir}/03_research/news_stories.md') as f:
            return f.read()
    except FileNotFoundError:
        return "News stories not found"
    except Exception as e:
        return f"Failed to load news stories: {str(e)}"


def read_business_profile(work_dir: str) -> str:
    """
    Load business profile from Perplexity research.

    Args:
        work_dir: Path to work directory

    Returns:
        str: Business profile markdown content
    """
    try:
        with open(f'{work_dir}/03_research/business_profile.md') as f:
            return f.read()
    except FileNotFoundError:
        return "Business profile not found"
    except Exception as e:
        return f"Failed to load business profile: {str(e)}"


def read_executive_profiles(work_dir: str) -> str:
    """
    Load executive profiles from Perplexity research.

    Args:
        work_dir: Path to work directory

    Returns:
        str: Executive profiles markdown content
    """
    try:
        with open(f'{work_dir}/03_research/executive_profiles.md') as f:
            return f.read()
    except FileNotFoundError:
        return "Executive profiles not found"
    except Exception as e:
        return f"Failed to load executive profiles: {str(e)}"


def read_sec_item1(work_dir: str) -> str:
    """
    Load SEC 10-K Item 1 (Business Description).

    Args:
        work_dir: Path to work directory

    Returns:
        str: Business description from 10-K
    """
    try:
        with open(f'{work_dir}/04_sec/10k_item1.txt') as f:
            content = f.read()
            # Truncate to first 10000 chars if too long
            if len(content) > 10000:
                return content[:10000] + "\n\n[... truncated for length ...]"
            return content
    except FileNotFoundError:
        return "SEC 10-K Item 1 not found"
    except Exception as e:
        return f"Failed to load SEC Item 1: {str(e)}"


def read_wikipedia_summary(work_dir: str) -> str:
    """
    Load Wikipedia company summary.

    Args:
        work_dir: Path to work directory

    Returns:
        str: Wikipedia summary text
    """
    try:
        with open(f'{work_dir}/05_wikipedia/wikipedia_summary.txt') as f:
            return f.read()
    except FileNotFoundError:
        return "Wikipedia summary not found"
    except Exception as e:
        return f"Failed to load Wikipedia summary: {str(e)}"


def read_business_model_analysis(work_dir: str) -> str:
    """
    Load business model analysis from deep analysis phase.

    Args:
        work_dir: Path to work directory

    Returns:
        str: Business model analysis markdown
    """
    try:
        with open(f'{work_dir}/06_analysis/business_model_analysis.md') as f:
            return f.read()
    except FileNotFoundError:
        return "Business model analysis not found"
    except Exception as e:
        return f"Failed to load business model analysis: {str(e)}"


def read_competitive_analysis(work_dir: str) -> str:
    """
    Load competitive landscape analysis.

    Args:
        work_dir: Path to work directory

    Returns:
        str: Competitive analysis markdown
    """
    try:
        with open(f'{work_dir}/06_analysis/competitive_analysis.md') as f:
            return f.read()
    except FileNotFoundError:
        return "Competitive analysis not found"
    except Exception as e:
        return f"Failed to load competitive analysis: {str(e)}"


def read_risk_analysis(work_dir: str) -> str:
    """
    Load risk and news analysis.

    Args:
        work_dir: Path to work directory

    Returns:
        str: Risk analysis markdown
    """
    try:
        with open(f'{work_dir}/06_analysis/risk_analysis.md') as f:
            return f.read()
    except FileNotFoundError:
        return "Risk analysis not found"
    except Exception as e:
        return f"Failed to load risk analysis: {str(e)}"


def read_investment_thesis(work_dir: str) -> str:
    """
    Load investment thesis with SWOT and bull/bear cases.

    Args:
        work_dir: Path to work directory

    Returns:
        str: Investment thesis markdown
    """
    try:
        with open(f'{work_dir}/06_analysis/investment_thesis.md') as f:
            return f.read()
    except FileNotFoundError:
        return "Investment thesis not found"
    except Exception as e:
        return f"Failed to load investment thesis: {str(e)}"


def read_peers_list(work_dir: str) -> List[Dict[str, Any]]:
    """
    Load list of peer companies.

    Args:
        work_dir: Path to work directory

    Returns:
        list: Peer companies data
    """
    try:
        with open(f'{work_dir}/01_technical/peers_list.json') as f:
            return json.load(f)
    except FileNotFoundError:
        return [{"error": "Peers list not found"}]
    except Exception as e:
        return [{"error": f"Failed to load peers list: {str(e)}"}]


def get_chart_path(work_dir: str) -> str:
    """
    Get path to stock chart image.

    Args:
        work_dir: Path to work directory

    Returns:
        str: Relative path to chart image
    """
    chart_path = '01_technical/chart.png'
    full_path = os.path.join(work_dir, chart_path)
    if os.path.exists(full_path):
        return chart_path
    else:
        return "Chart not found"


# Helper function to get all available data for a section
def get_section_data(work_dir: str, section: str) -> Dict[str, Any]:
    """
    Load all relevant data for a specific report section.

    Args:
        work_dir: Path to work directory
        section: Section name (e.g., 'executive_summary', 'business_model')

    Returns:
        dict: All relevant data for the section
    """
    data_loaders = {
        'executive_summary': [
            ('technical', read_technical_analysis),
            ('fundamentals', read_fundamentals),
            ('investment_thesis', read_investment_thesis)
        ],
        'extended_profile': [
            ('wikipedia', read_wikipedia_summary),
            ('sec_item1', read_sec_item1),
            ('news', read_news_stories),
            ('business_profile', read_business_profile)
        ],
        'business_model': [
            ('business_model_analysis', read_business_model_analysis),
            ('fundamentals', read_fundamentals),
            ('business_profile', read_business_profile)
        ],
        'competitive_landscape': [
            ('competitive_analysis', read_competitive_analysis),
            ('peers', read_peers_list),
            ('key_ratios', read_key_ratios)
        ],
        'supply_chain': [
            ('sec_item1', read_sec_item1),
            ('business_profile', read_business_profile)
        ],
        'financial_leverage': [
            ('balance_sheet', read_balance_sheet),
            ('cash_flow', read_cash_flow),
            ('key_ratios', read_key_ratios),
            ('fundamentals', read_fundamentals)
        ],
        'news_risks': [
            ('risk_analysis', read_risk_analysis),
            ('news', read_news_stories),
            ('analyst_recommendations', read_analyst_recommendations)
        ],
        'conclusion': [
            ('investment_thesis', read_investment_thesis),
            ('technical', read_technical_analysis),
            ('fundamentals', read_fundamentals)
        ]
    }

    loaders = data_loaders.get(section, [])
    result = {}

    for key, loader_func in loaders:
        result[key] = loader_func(work_dir)

    return result


if __name__ == '__main__':
    # Test the tools
    import sys
    if len(sys.argv) < 2:
        print("Usage: ./agent_tools.py <work_dir>")
        sys.exit(1)

    work_dir = sys.argv[1]

    print("Testing agent tools...")
    print(f"Work directory: {work_dir}")
    print("\n" + "="*60)

    print("\nTechnical Analysis:")
    tech = read_technical_analysis(work_dir)
    print(f"  Latest price: {tech.get('latest_price', 'N/A')}")

    print("\nFundamentals:")
    fund = read_fundamentals(work_dir)
    print(f"  Company: {fund.get('Name', 'N/A')}")
    print(f"  Sector: {fund.get('Sector', 'N/A')}")

    print("\nChart path:")
    print(f"  {get_chart_path(work_dir)}")

    print("\n" + "="*60)
    print("✓ Agent tools test complete")
