#!/opt/anaconda3/envs/fidelity/bin/python3
"""
Deep Research Phase using Claude Agent SDK with MCP Tools

Reads research_report.md and performs comprehensive deep analysis
using Claude Sonnet 4.5 with extended thinking and access to
6 MCP servers providing financial research tools.

Usage:
    ./skills/research_deep.py SYMBOL [--work-dir DIR] [--no-tools]

Output:
    - 08_deep_research/deep_research_output.md
    - 08_deep_research/deep_research_thinking.md
    - 08_deep_research/tool_usage.txt (if tools used)
"""

import os
import sys
import argparse
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import dotenv

# Try Claude Agent SDK imports, fall back to basic Anthropic if not available
try:
    from claude_agent_sdk import (
        ClaudeSDKClient,
        ClaudeAgentOptions,
        AssistantMessage,
        TextBlock
    )
    AGENT_SDK_AVAILABLE = True
except ImportError:
    AGENT_SDK_AVAILABLE = False
    print("⚠ Warning: claude-agent-sdk not installed. MCP tools will not be available.")
    print("  Install with: pip install claude-agent-sdk")

# Basic Anthropic SDK for fallback
from anthropic import Anthropic


def load_research_report(work_dir):
    """Load the initial research report as context."""
    report_path = os.path.join(work_dir, 'research_report.md')
    if not os.path.exists(report_path):
        raise FileNotFoundError(f"Research report not found: {report_path}")

    with open(report_path, 'r') as f:
        content = f.read()

    # Extract company name from report (first line after "Company:")
    company_name = None
    for line in content.split('\n'):
        if line.startswith('**Company:**'):
            company_name = line.replace('**Company:**', '').strip()
            break

    return content, company_name


def load_mcp_server_configs() -> Dict[str, Any]:
    """
    Load MCP server configurations from claude_desktop_config.json.

    Returns:
        dict: MCP server configurations for ClaudeAgentOptions
    """
    config_path = os.path.expanduser(
        "~/Library/Application Support/Claude/claude_desktop_config.json"
    )

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Claude config not found: {config_path}")

    with open(config_path, 'r') as f:
        claude_config = json.load(f)

    mcp_servers = {}

    # Target servers for deep research
    # Testing with single server to avoid Claude Agent SDK bug with multiple servers
    # Bug: https://github.com/anthropics/claude-code/issues/10668
    server_names = [
        'stock-symbol-server',  # Our custom financial tools (6 tools)
    ]

    for server_name in server_names:
        if server_name in claude_config.get('mcpServers', {}):
            server_config = claude_config['mcpServers'][server_name]

            # Convert to ClaudeAgentOptions format
            mcp_servers[server_name] = {
                'type': 'stdio',
                'command': server_config['command'],
                'args': server_config.get('args', []),
                'env': server_config.get('env', {})
            }

    return mcp_servers


async def run_deep_research_with_tools(
    symbol: str,
    company_name: str,
    report_content: str
) -> Tuple[str, str, str]:
    """
    Call Claude Agent SDK with MCP tools and research report context.

    Hybrid mode: Provides research_report.md as context while giving
    Claude access to all MCP tools for verification and gap-filling.

    Note: API key is handled via ~/.claude/ configuration, not environment variables.

    Returns:
        tuple: (analysis_output, thinking_process, tool_usage_summary)
    """
    # Load MCP server configurations
    print("\nConfiguring MCP servers...")
    try:
        mcp_servers = load_mcp_server_configs()
        print(f"✓ Loaded {len(mcp_servers)} MCP server configurations")
        for server_name in mcp_servers.keys():
            print(f"  - {server_name}")
    except Exception as e:
        print(f"⚠ Warning: Could not load MCP servers: {e}")
        print("  Continuing with basic mode (no tools)")
        mcp_servers = {}

    # Create Claude Agent options
    # Note: API key is handled via ~/.claude/ configuration
    # Model defaults to claude-sonnet-4-5
    options = ClaudeAgentOptions(
        mcp_servers=mcp_servers,
        cwd=os.getcwd(),
        # Auto-approve tool usage for autonomous research
        allowed_tools=["*"],  # Allow all MCP tools
    )

    company_display = company_name if company_name else symbol

    # Enhanced prompt for hybrid mode
    prompt = f"""I have collected comprehensive information on {company_display} (symbol {symbol}) in the research_report.md file provided below.

You have access to powerful financial research tools through MCP servers. Use these tools to:
- Fill gaps in the provided research
- Verify critical facts and figures
- Find recent developments not covered in the report
- Gather additional market data and competitive intelligence

Write a comprehensive report on {symbol} in the straightforward factual style of a Wall Street equity research analyst, in 9 sections:

1. Short summary overall assessment:
   One-sentence summary of section 9 with evaluation of risk/reward profile

2. Extended Profile:
   • History with origin story and key historical milestones
   • Core business and competitors
   • Recent major news

3. Business Model:
   • Describe their core businesses, products and services.
   • Outline their key revenue streams, customer segments, and monetization strategies.
   • Analyze key characteristics of markets it operates in:
     - customer acquisition costs
     - retention metrics
     - sales cycles
     - seasonal or cyclical business patterns
     - margins, market size, growth trajectory and factors affecting them
   • Explain sources of competitive advantage such as network effects, switching costs, brands, intellectual property, regulatory moats, and other barriers to entry.

4. Competitive Landscape:
   • Identify their main competitors, including direct, adjacent, and emerging competitors.
   • Compare key metrics such as market share, product differentiation, pricing power, and growth trajectories.

5. Supply Chain Positioning:
   • Describe their role in the upstream (supplier-side) and downstream (customer/distribution) parts of the supply chain.
   • Identify key suppliers, partners, distributors, and any major dependencies or concentrations.

6. Financial and Operating Leverage:
   • Analyze the company's use of financial leverage (debt levels, interest obligations, credit ratings).
   • Analyze operating leverage (fixed vs. variable cost structure, scalability, margin sensitivity to revenue changes).
   • Analyze cash flow generation and working capital dynamics.
   • Analyze capital allocation strategy (dividends, buybacks, reinvestment).

7. Valuation:
    • Identify appropriate valuation methodologies, including income-based (e.g., DCF), asset-based (e.g. book value and sum of parts), market-based (e.g. peer multiples and comparisons), and LBO analysis
    • Highlight important valuation inputs and metrics (growth rates, margins, discount rates, terminal value assumptions).
    • Summarize current ratings and analyst opinions, including recent changes.
    • Note the stock's volatility, liquidity, if it is widely covered and owned, if it is a hedge fund story stock or meme stock, what macro factors it is sensitive to

8. Recent developments, News Search and Risk Factors:
    For this section, use your MCP tools to conduct deep research:
    • Search for: {company_display} + "analyst report" OR "research note" downgrade OR upgrade
    • Use perplexity to search: "What are the most significant investigative reports and executive profiles about {company_display} published in 2024-2025?"
    • Look for: revenue trends, management changes, product launches, M&A, restructurings
    • Investigate: short-seller reports, regulatory investigations, lawsuits
    • Check for: product failures, supply chain disruptions
    • Find: major wins, partnerships, large customer acquisitions
    • Research: insider trading patterns and institutional ownership changes
    • Consider: potential acquirers or acquisition targets
    • Note any other key themes or trends that you think are important

9. Conclusion:
    • Summarize the company's strategic position and the stock's investment risk/reward profile
    • Strengths, weaknesses, opportunities, threats (SWOT)
    • Bear case and bull case
    • The level of risk
    • Any critical "watch points" for further due diligence and ongoing monitoring

Use a straightforward, factual tone throughout the analysis. Focus on data and observable facts rather than speculation.

---

Here is the research report collected so far:

{report_content}
"""

    print(f"\nInitializing Claude Agent SDK client...")
    print(f"Model: claude-sonnet-4-5-20250929")
    print(f"MCP servers: {len(mcp_servers)}")

    try:
        async with ClaudeSDKClient(options=options) as client:
            print(f"✓ Claude Agent SDK client initialized")
            print(f"Starting agentic research loop...")
            print(f"This may take several minutes as Claude uses tools...")

            # Send initial query
            await client.query(prompt)

            # Collect response and thinking
            analysis_blocks = []
            thinking_blocks = []
            tool_usage = []

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            analysis_blocks.append(block.text)
                        elif hasattr(block, 'thinking'):
                            thinking_blocks.append(block.thinking)
                        elif hasattr(block, 'tool_use'):
                            tool_info = f"{block.tool_use.name}({block.tool_use.input})"
                            tool_usage.append(tool_info)
                            print(f"  🔧 Tool used: {tool_info}")

            analysis = "\n\n".join(analysis_blocks)
            thinking = "\n\n---\n\n".join(thinking_blocks)
            tool_summary = f"Tools used ({len(tool_usage)}):\n" + "\n".join(f"- {t}" for t in tool_usage)

            return analysis, thinking, tool_summary

    except Exception as e:
        print(f"\n❌ Error in Claude Agent SDK: {e}")
        print("\nFalling back to basic mode without tools...")
        import traceback
        traceback.print_exc()
        # Fall back to basic mode
        return run_deep_research_basic(symbol, company_name, report_content)


def run_deep_research_basic(symbol, company_name, report_content):
    """
    Fallback: Basic Anthropic SDK without tools.

    This is the existing implementation for graceful degradation
    when MCP servers fail to connect or Agent SDK is not available.

    Returns:
        tuple: (analysis_output, thinking_process, None)
    """
    dotenv.load_dotenv()
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    client = Anthropic(api_key=api_key)

    # Use company_name if available, otherwise use symbol
    company_display = company_name if company_name else symbol

    prompt = f"""I have collected information on {company_display} (symbol {symbol}) from various tools in the research_report.md file.

Using everything found so far and everything you can find by using tools and doing deep research, write a report on {symbol} in the straightforward factual style of a Wall Street equity research analyst, in 9 sections:

Include links to sources at the end of each paragraph.

1. Introduction:
   One-sentence summary of section 9 with evaluation of risk/reward profile

2. Company Profile:
   • History with origin story and key historical milestones
   • Core business and competitors
   • Recent major news

3. Business Model:
   • Describe their core businesses, products and services.
   • Outline their key revenue streams, customer segments, and monetization strategies.
   • Analyze key characteristics of markets it operates in:
     - customer acquisition costs
     - retention metrics
     - sales cycles
     - seasonal or cyclical business patterns
     - margins, market size, growth trajectory and factors affecting them
   • Explain sources of competitive advantage such as network effects, switching costs, brands, intellectual property, regulatory moats, and other barriers to entry.

4. Competitive Landscape:
   • Identify their main competitors, including direct, adjacent, and emerging competitors.
   • Compare key metrics such as market share, product differentiation, pricing power, and growth trajectories.

5. Supply Chain Positioning:
   • Describe their role in the upstream (supplier-side) and downstream (customer/distribution) parts of the supply chain.
   • Identify key suppliers, partners, distributors, and any major dependencies or concentrations.

6. Financial and Operating Leverage:
   • Analyze the company's use of financial leverage (debt levels, interest obligations, credit ratings).
   • Analyze operating leverage (fixed vs. variable cost structure, scalability, margin sensitivity to revenue changes).
   • Analyze cash flow generation and working capital dynamics.
   • Analyze capital allocation strategy (dividends, buybacks, reinvestment).

7. Valuation:
    • Identify appropriate valuation methodologies, including income-based (e.g., DCF), asset-based (e.g. book value and sum of parts), market-based (e.g. peer multiples and comparisons), and LBO analysis
    • Highlight important valuation inputs and metrics (growth rates, margins, discount rates, terminal value assumptions).
    • Summarize current ratings and analyst opinions, including recent changes.
    • Note the stock's volatility, liquidity, if it is widely covered and owned, if it is a hedge fund story stock or meme stock, what macro factors it is sensitive to

8. Recent developments, News Search and Risk Factors:
    • Conduct a deep news search for significant positive and negative news items over the last 12 months, including:
      - company + "analyst report" OR "research note" downgrade OR upgrade
      - use perplexity to search for company + "profile" or "executive profile" and ask: "What are the most significant investigative reports and executive profiles about {company_display} published in 2023-2024?"
      - Revenue and earnings trends
      - Management changes
      - New product launches
      - Restructurings, mergers, acquisitions, divestitures, strategic partnerships
      - Short-seller reports or allegations.
      - Regulatory investigations or lawsuits.
      - Product failures, operational issues, or supply chain disruptions.
      - Major wins (e.g., partnerships, large customer wins, successful product launches).
      - Insider trading activity and institutional ownership changes
    • Summarize key themes from recent media coverage, analyst reports, and public filings.
    • Note controversies, reputational risks, and governance concerns if any.
    • Discuss what companies might be potential acquisition targets or acquirers of the company, based on overlapping or complementary customer bases, product offerings, and technical capabilities.
    • Note any other key themes or trends that you think are important.

9. Conclusion:
    • Summarize the company's strategic position and the stock's investment risk/reward profile
    • Strengths, weaknesses, opportunities, threats (SWOT)
    • Bear case and bull case
    • The level of risk
    • Any critical "watch points" for further due diligence and ongoing monitoring.

Use a straightforward, factual tone throughout the analysis. Focus on data and observable facts rather than speculation.
"""

    print(f"\nCalling Claude API...")
    print(f"Model: claude-sonnet-4-5-20250929")
    print(f"Extended thinking: Enabled (10K token budget)")

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=16000,
            thinking={
                "type": "enabled",
                "budget_tokens": 10000
            },
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\n---\n\nHere is the research report:\n\n{report_content}"
                }
            ]
        )

        # Extract thinking and text content
        thinking_blocks = []
        text_blocks = []

        for block in message.content:
            if block.type == "thinking":
                thinking_blocks.append(block.thinking)
            elif block.type == "text":
                text_blocks.append(block.text)

        analysis = "\n\n".join(text_blocks)
        thinking = "\n\n---\n\n".join(thinking_blocks)

        return analysis, thinking, None

    except Exception as e:
        print(f"\n❌ Error calling Claude API: {e}")
        raise


def save_outputs(work_dir, analysis, thinking, tool_summary=None):
    """Save deep research outputs including tool usage summary."""
    output_dir = os.path.join(work_dir, '08_deep_research')
    os.makedirs(output_dir, exist_ok=True)

    # Save analysis
    analysis_path = os.path.join(output_dir, 'deep_research_output.md')
    with open(analysis_path, 'w') as f:
        f.write(analysis)
    print(f"✓ Saved: {analysis_path}")

    # Save thinking process
    thinking_path = os.path.join(output_dir, 'deep_research_thinking.md')
    with open(thinking_path, 'w') as f:
        f.write(f"# Extended Thinking Process\n\n{thinking}")
    print(f"✓ Saved: {thinking_path}")

    # Save tool usage summary (NEW)
    if tool_summary:
        tool_path = os.path.join(output_dir, 'tool_usage.txt')
        with open(tool_path, 'w') as f:
            f.write(tool_summary)
        print(f"✓ Saved: {tool_path}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Deep research phase using Claude Agent SDK with MCP tools'
    )
    parser.add_argument('symbol', help='Stock ticker symbol')
    parser.add_argument(
        '--work-dir',
        default=None,
        help='Work directory path (default: work/SYMBOL_YYYYMMDD)'
    )
    parser.add_argument('--no-tools', action='store_true',
                       help='Disable MCP tools (basic mode only)')
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

    print("="*60)
    print("Deep Research Phase - Claude Agent SDK with MCP Tools")
    print("="*60)
    print(f"Symbol: {symbol}")
    print(f"Work Directory: {work_dir}")
    print(f"Tools Enabled: {not args.no_tools}")
    if not AGENT_SDK_AVAILABLE:
        print(f"⚠ Agent SDK not available - forced basic mode")
    print("="*60)

    try:
        # Load research report
        print(f"\nLoading research report...")
        report_content, company_name = load_research_report(work_dir)
        print(f"✓ Loaded research report ({len(report_content)} characters)")
        if company_name:
            print(f"✓ Company: {company_name}")

        # Run deep research
        print(f"\nAnalyzing {symbol} with Claude Sonnet 4.5...")

        if args.no_tools or not AGENT_SDK_AVAILABLE:
            if args.no_tools:
                print("Basic mode (--no-tools flag)")
            else:
                print("Basic mode (Agent SDK not available)")
            analysis, thinking, tool_summary = run_deep_research_basic(
                symbol, company_name, report_content
            )
        else:
            # Run async function with MCP tools
            print("Advanced mode (MCP tools enabled)")
            analysis, thinking, tool_summary = asyncio.run(
                run_deep_research_with_tools(symbol, company_name, report_content)
            )

        print(f"✓ Analysis complete ({len(analysis)} characters)")
        if thinking:
            print(f"✓ Thinking process captured ({len(thinking)} characters)")
        if tool_summary:
            print(f"✓ Tool usage recorded")

        # Save outputs
        print(f"\nSaving outputs...")
        save_outputs(work_dir, analysis, thinking, tool_summary)

        print("\n" + "="*60)
        print("SUCCESS: Deep research completed!")
        print("="*60)
        return 0

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure research_report.md has been generated first.")
        print("Run with --phases report before running deep research.")
        return 1

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure ANTHROPIC_API_KEY is set in your .env file.")
        return 1

    except Exception as e:
        print(f"\n❌ Error in deep research: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
