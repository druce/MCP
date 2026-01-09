#!/opt/anaconda3/envs/fidelity/bin/python3
"""
Deep Research Phase using Claude API

Reads research_report.md and performs comprehensive deep analysis
using Claude Sonnet 4.5 with extended thinking.

Usage:
    ./skills/research_deep.py SYMBOL [--work-dir DIR]

Output:
    - 08_deep_research/deep_research_output.md
    - 08_deep_research/deep_research_thinking.md
"""

import os
import sys
import argparse
from datetime import datetime
from anthropic import Anthropic
import dotenv


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


def run_deep_research(symbol, company_name, report_content):
    """
    Call Claude API with extended thinking to perform deep research.

    Returns:
        tuple: (analysis_output, thinking_process)
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

1. Short summary overall assessment:
   One-sentence summary of section 12 with evaluation of risk/reward profile

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

Use a straightforward, factual tone throughout the analysis. Focus on data and observable facts rather than speculation."""

    print(f"\nCalling Claude API...")
    print(f"Model: claude-sonnet-4.5")
    print(f"Extended thinking: Enabled (10K token budget)")

    try:
        message = client.messages.create(
            model="claude-sonnet-4.5",
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

        return analysis, thinking

    except Exception as e:
        print(f"\n❌ Error calling Claude API: {e}")
        raise


def save_outputs(work_dir, analysis, thinking):
    """Save deep research outputs."""
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

    return True


def main():
    parser = argparse.ArgumentParser(description='Deep research phase using Claude API')
    parser.add_argument('symbol', help='Stock ticker symbol')
    parser.add_argument('--work-dir', required=True, help='Work directory path')
    args = parser.parse_args()

    symbol = args.symbol.upper()

    print("="*60)
    print("Deep Research Phase - Claude API with Extended Thinking")
    print("="*60)
    print(f"Symbol: {symbol}")
    print(f"Work Directory: {args.work_dir}")
    print("="*60)

    try:
        # Load research report
        print(f"\nLoading research report...")
        report_content, company_name = load_research_report(args.work_dir)
        print(f"✓ Loaded research report")
        if company_name:
            print(f"✓ Company: {company_name}")

        # Run deep research
        print(f"\nAnalyzing {symbol} with Claude Sonnet 4.5...")
        print("This may take 30-60 seconds with extended thinking enabled...")

        analysis, thinking = run_deep_research(symbol, company_name, report_content)

        print(f"✓ Analysis complete ({len(analysis)} characters)")
        print(f"✓ Thinking process captured ({len(thinking)} characters)")

        # Save outputs
        print(f"\nSaving outputs...")
        save_outputs(args.work_dir, analysis, thinking)

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
