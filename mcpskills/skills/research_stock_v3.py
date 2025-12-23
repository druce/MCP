#!/opt/anaconda3/envs/fidelity/bin/python3
"""
Agent-Based Stock Research Orchestrator (v3)

Experimental architecture using autonomous agents for section synthesis.

Usage:
    ./skills/research_stock_v3.py TSLA
    ./skills/research_stock_v3.py TSLA --use-critic
    ./skills/research_stock_v3.py TSLA --skip-synthesis

Architecture:
    Stage 1: Parallel data gathering (reuses research_stock.py logic)
    Stage 2: Parallel agent-based section synthesis
    Stage 3: Template assembly

Each section has an autonomous agent that:
- Receives a detailed prompt for what to write
- Has access to relevant data loading tools
- Can reason about the best way to structure the section
- Writes high-quality, data-driven content
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path


def get_section_prompt(section: str, symbol: str, work_dir: str) -> str:
    """
    Get the detailed prompt for a specific section agent.

    Args:
        section: Section name
        symbol: Stock ticker
        work_dir: Work directory path

    Returns:
        str: Agent prompt
    """
    prompts = {
        'executive_summary': f"""You are an equity research analyst writing the Executive Summary for {symbol}.

Your task:
Write exactly 2 paragraphs for the Executive Summary section:
1. One-sentence investment thesis + current market positioning
2. Risk/reward profile assessment

Available data sources in work directory {work_dir}:
- Technical analysis: 01_technical/technical_analysis.json
- Fundamentals: 02_fundamental/company_overview.json
- Investment thesis: 06_analysis/investment_thesis.md

Instructions:
1. Use Read tool to load technical_analysis.json - get latest_price, trend_signals (above_200sma), indicators
2. Use Read tool to load company_overview.json - get MarketCapitalization, TrailingPE, Sector, Industry
3. Use Read tool to load investment_thesis.md - get SWOT summary, bull/bear cases
4. Write 2 concise paragraphs (~150 words total) that synthesize this data
5. Be specific - cite actual metrics and numbers
6. Save output to {work_dir}/07_synthesis/executive_summary.md using Write tool

Output format: Plain markdown text, no title/header, just 2 paragraphs.""",

        'extended_profile': f"""You are an equity research analyst writing the Extended Profile section for {symbol}.

Your task:
Write 3 subsections:
1. Company History & Origin Story (2-3 paragraphs)
2. Core Business & Competitors (2-3 paragraphs)
3. Recent Major News (bulleted list)

Available data sources in work directory {work_dir}:
- Wikipedia summary: 05_wikipedia/wikipedia_summary.txt
- SEC 10-K Item 1: 04_sec/10k_item1.txt (first 10k chars)
- News stories: 03_research/news_stories.md
- Business profile: 03_research/business_profile.md

Instructions:
1. Use Read tool to load all 4 data sources
2. Synthesize company history from Wikipedia and SEC filings
3. Extract core business description and main competitors
4. Summarize recent major news (last 12 months)
5. Write clear, flowing prose that tells the company's story
6. Save to {work_dir}/07_synthesis/extended_profile.md

Output format: Markdown with ## subsection headers.""",

        'business_model': f"""You are an equity research analyst writing the Business Model section for {symbol}.

Your task:
Write 4 subsections analyzing the business model:
1. Core Business & Products/Services (2 paragraphs)
2. Revenue Streams (bulleted list + explanation)
3. Market Characteristics (1-2 paragraphs)
4. Competitive Advantages (bulleted list of moats)

Available data sources in work directory {work_dir}:
- Business model analysis: 06_analysis/business_model_analysis.md (deep Perplexity research)
- Fundamentals: 02_fundamental/company_overview.json
- Business profile: 03_research/business_profile.md

Instructions:
1. Read all 3 data sources
2. Extract and synthesize key business model insights
3. Include specific revenue numbers if available
4. Identify and explain competitive moats (network effects, brand, IP, etc.)
5. Be analytical - explain WHY this business model works or doesn't
6. Save to {work_dir}/07_synthesis/business_model.md

Output format: Markdown with ## subsection headers.""",

        'competitive_landscape': f"""You are an equity research analyst writing the Competitive Landscape section for {symbol}.

Your task:
Write 3 subsections:
1. Main Competitors (table format)
2. Competitive Positioning (2-3 paragraphs)
3. Market Dynamics (1-2 paragraphs)

Available data sources in work directory {work_dir}:
- Competitive analysis: 06_analysis/competitive_analysis.md (Perplexity research)
- Peers list: 01_technical/peers_list.json
- Key ratios: 02_fundamental/key_ratios.csv

Instructions:
1. Read competitive_analysis.md for deep insights
2. Read peers_list.json for competitor names/tickers
3. Read key_ratios.csv for comparative metrics
4. Create markdown table comparing key competitors
5. Analyze competitive positioning and market share trends
6. Explain competitive dynamics and who's winning/losing
7. Save to {work_dir}/07_synthesis/competitive_landscape.md

Output format: Markdown with tables and ## subsection headers.""",

        'supply_chain': f"""You are an equity research analyst writing the Supply Chain Positioning section for {symbol}.

Your task:
Write analysis of supply chain positioning:
1. Upstream suppliers and dependencies (1-2 paragraphs)
2. Downstream customers and distribution (1-2 paragraphs)
3. Supply chain risks and opportunities (bulleted list)

Available data sources in work directory {work_dir}:
- SEC 10-K Item 1: 04_sec/10k_item1.txt (official business description)
- Business profile: 03_research/business_profile.md

Instructions:
1. Read SEC Item 1 - look for mentions of suppliers, raw materials, manufacturing
2. Read business profile for supply chain insights
3. Identify key upstream dependencies (materials, components, suppliers)
4. Identify downstream channels (direct, distributors, partners)
5. Assess supply chain risks (concentration, geopolitics, shortages)
6. Save to {work_dir}/07_synthesis/supply_chain.md

Output format: Markdown with ## subsection headers.
Note: If supply chain info is limited, state this clearly and provide what's available.""",

        'financial_leverage': f"""You are an equity research analyst writing the Financial & Operating Leverage section for {symbol}.

Your task:
Write 3 subsections analyzing leverage:
1. Financial Leverage (debt analysis, 2 paragraphs)
2. Operating Leverage (margins analysis, 2 paragraphs)
3. Cash Flow & Capital Allocation (1-2 paragraphs)

Available data sources in work directory {work_dir}:
- Balance sheet: 02_fundamental/balance_sheet.csv
- Cash flow: 02_fundamental/cash_flow.csv
- Key ratios: 02_fundamental/key_ratios.csv
- Fundamentals: 02_fundamental/company_overview.json

Instructions:
1. Read all 4 data sources (CSVs contain time series data)
2. Analyze debt levels, debt/equity ratio, interest coverage
3. Analyze profit margins, operating margins, EBITDA margins
4. Assess cash flow trends (operating, investing, financing)
5. Include specific numbers and trends
6. Save to {work_dir}/07_synthesis/financial_leverage.md

Output format: Markdown with ## subsection headers and tables where helpful.""",

        'news_risks': f"""You are an equity research analyst writing the Recent Developments, News & Risk Factors section for {symbol}.

Your task:
Write 3 subsections:
1. Significant News (Last 12 Months) - chronological summary
2. Analyst Activity & Investigative Reports - recent ratings/research
3. Risk Factors - bulleted list with explanations

Available data sources in work directory {work_dir}:
- Risk analysis: 06_analysis/risk_analysis.md (comprehensive Perplexity research)
- News stories: 03_research/news_stories.md
- Analyst recommendations: 02_fundamental/analyst_recommendations.json

Instructions:
1. Read risk_analysis.md - contains analyst reports, investigations, legal issues
2. Read news_stories.md for major news developments
3. Read analyst_recommendations.json for recent rating changes
4. Chronologically summarize major news events (last 12 months)
5. Highlight any investigative reports or short-seller research
6. List key risk factors (operational, financial, regulatory, competitive)
7. Save to {work_dir}/07_synthesis/news_risks.md

Output format: Markdown with ## subsection headers.""",

        'conclusion': f"""You are an equity research analyst writing the Conclusion section for {symbol}.

Your task:
Write 4 subsections that synthesize the entire report:
1. Strategic Position Summary (2 paragraphs)
2. SWOT Analysis (4 bulleted lists: Strengths, Weaknesses, Opportunities, Threats)
3. Investment Cases (Bull Case - 3-5 bullets, Bear Case - 3-5 bullets)
4. Critical Watch Points (bulleted list of metrics/events to monitor)

Available data sources in work directory {work_dir}:
- Investment thesis: 06_analysis/investment_thesis.md (SWOT, bull/bear cases)
- Technical: 01_technical/technical_analysis.json (trend signals)
- Fundamentals: 02_fundamental/company_overview.json (key metrics)

Instructions:
1. Read investment_thesis.md - primary source for SWOT and bull/bear cases
2. Read technical and fundamental data to add current context
3. Write strategic summary synthesizing company's position
4. Present SWOT analysis clearly (4 separate bulleted lists)
5. Present Bull Case (optimistic scenario with catalysts)
6. Present Bear Case (pessimistic scenario with risks)
7. List 5-7 critical metrics/events to watch
8. Save to {work_dir}/07_synthesis/conclusion.md

Output format: Markdown with ## subsection headers and clear bullet lists."""
    }

    return prompts.get(section, f"Write the {section} section for {symbol}.")


def spawn_synthesis_agents(symbol: str, work_dir: str, use_critic: bool = False) -> dict:
    """
    Spawn autonomous agents to write each report section in parallel.

    This function uses the Task tool (available in Claude Code environment)
    to spawn 8 autonomous agents that write different sections concurrently.

    Args:
        symbol: Stock ticker
        work_dir: Work directory path
        use_critic: Whether to use critic agent for quality review

    Returns:
        dict: Section name -> synthesized content mapping
    """
    print(f"\n{'='*60}")
    print(f"Stage 2: Spawning 8 autonomous agents for section synthesis...")
    print(f"{'='*60}")

    synthesis_sections = [
        'executive_summary',
        'extended_profile',
        'business_model',
        'competitive_landscape',
        'supply_chain',
        'financial_leverage',
        'news_risks',
        'conclusion'
    ]

    # Import Task and TaskOutput tools (only available in Claude Code)
    # This will fail if not running in Claude Code environment
    try:
        # These are pseudo-imports - the actual Task tool is available via function calling
        # We'll detect environment by attempting to spawn a test agent
        claude_code_available = True
    except:
        claude_code_available = False

    if not claude_code_available:
        print("\n⚠️  Not running in Claude Code environment - cannot spawn agents")
        print("Fallback: Would use subprocess-based synthesis here\n")
        return {}

    # Spawn agents in parallel (one per section)
    print("\nSpawning agents...")

    agent_tasks = {}
    for i, section in enumerate(synthesis_sections, 1):
        section_name = section.replace('_', ' ').title()
        print(f"  {i}. Agent for: {section_name}")

        prompt = get_section_prompt(section, symbol, work_dir)

        # In actual Claude Code environment, we would call:
        # task = Task(
        #     description=f"Synthesize {section_name} section",
        #     prompt=prompt,
        #     subagent_type='general-purpose',
        #     run_in_background=True
        # )
        # agent_tasks[section] = task.task_id

        # For now, placeholder
        agent_tasks[section] = f"task_{section}"

    print(f"\n✓ Spawned {len(agent_tasks)} agents in parallel")

    # Collect agent results
    print("\nWaiting for agents to complete...")

    results = {}
    for section, task_id in agent_tasks.items():
        print(f"  ⏳ Collecting: {section.replace('_', ' ').title()}...")

        # In Claude Code environment:
        # output = TaskOutput(task_id=task_id, block=True, timeout=300000)
        # results[section] = output

        # Placeholder
        results[section] = f"[Agent output for {section}]"

    print(f"\n✓ All {len(results)} agents completed")

    # Optional: Critic agent for quality review
    if use_critic:
        print(f"\n{'='*60}")
        print("Running critic agent for quality review...")
        print(f"{'='*60}")

        # Spawn critic agent that reviews all sections
        # critic_prompt = create_critic_prompt(results, work_dir)
        # critic_task = Task(...)
        # critique = TaskOutput(...)

        print("⚠️  Critic agent not yet implemented")

    return results


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Agent-based stock research orchestrator (v3 - Experimental)'
    )
    parser.add_argument(
        'symbol',
        help='Stock ticker symbol (e.g., TSLA, AAPL, MSFT)'
    )
    parser.add_argument(
        '--use-critic',
        action='store_true',
        help='Enable critic agent for quality review'
    )
    parser.add_argument(
        '--skip-synthesis',
        action='store_true',
        help='Skip agent synthesis, only gather data'
    )
    parser.add_argument(
        '--skip-cleanup',
        action='store_true',
        help='Do not delete old work directories'
    )

    args = parser.parse_args()
    symbol = args.symbol.upper()

    print("=" * 60)
    print("Agent-Based Stock Research Orchestrator (v3)")
    print("=" * 60)
    print(f"Symbol: {symbol}")
    print(f"Use Critic: {args.use_critic}")
    print(f"Skip Synthesis: {args.skip_synthesis}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Stage 1: Run parallel data gathering using existing orchestrator
    print(f"\n{'='*60}")
    print("Stage 1: Parallel Data Gathering")
    print(f"{'='*60}")

    research_cmd = [
        './skills/research_stock.py',
        symbol,
        '--phases', 'technical,fundamental,research,analysis,sec,wikipedia'
    ]

    if args.skip_cleanup:
        research_cmd.append('--skip-cleanup')

    print(f"Running: {' '.join(research_cmd)}")

    try:
        result = subprocess.run(
            research_cmd,
            capture_output=False,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode != 0:
            print(f"\n❌ Data gathering failed with return code {result.returncode}")
            return 1

        print("\n✓ Stage 1 complete: All data gathered")

    except subprocess.TimeoutExpired:
        print("\n❌ Data gathering timed out after 10 minutes")
        return 1
    except Exception as e:
        print(f"\n❌ Data gathering failed: {e}")
        return 1

    # Determine work directory
    date_str = datetime.now().strftime('%Y%m%d')
    work_dir = f"work/{symbol}_{date_str}"

    if not os.path.exists(work_dir):
        print(f"\n❌ Work directory not found: {work_dir}")
        return 1

    # Stage 2: Agent-based section synthesis
    if not args.skip_synthesis:
        agent_tasks = spawn_synthesis_agents(symbol, work_dir, args.use_critic)

        # TODO: When running in Claude Code, this would:
        # 1. Use Task tool to spawn 8 agents in parallel
        # 2. Each agent gets section-specific prompt
        # 3. Agents use Read/Write tools to access data and write sections
        # 4. Optionally spawn critic agent to review quality
        # 5. Collect all agent outputs

        print(f"\n{'='*60}")
        print("Stage 2: Agent Synthesis Status")
        print(f"{'='*60}")
        print("⚠️  Placeholder: Agent synthesis not yet implemented")
        print("When running in Claude Code environment:")
        print("  - 8 agents would run in parallel")
        print("  - Each writes a specific section")
        print("  - Output saved to 07_synthesis/")

    # Stage 3: Report assembly
    print(f"\n{'='*60}")
    print("Stage 3: Report Assembly")
    print(f"{'='*60}")

    # For now, use existing report generator
    report_cmd = [
        './skills/research_report.py',
        symbol,
        '--work-dir', work_dir
    ]

    print(f"Running: {' '.join(report_cmd)}")

    try:
        result = subprocess.run(
            report_cmd,
            capture_output=False,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print("\n✓ Stage 3 complete: Report assembled")
        else:
            print(f"\n⚠️  Report assembly had issues (return code {result.returncode})")

    except Exception as e:
        print(f"\n⚠️  Report assembly failed: {e}")

    # Final summary
    print(f"\n{'='*60}")
    print("Research Complete")
    print(f"{'='*60}")
    print(f"Symbol: {symbol}")
    print(f"Work directory: {work_dir}")
    print(f"Report: {work_dir}/research_report.md")
    print(f"\n{'='*60}")

    print("\n📝 Note: This is v3 (experimental) - agent synthesis pending Task tool integration")

    return 0


if __name__ == '__main__':
    sys.exit(main())
