# Equity Research and Portfolio Management Skills

A collection of Claude Code skills for automated equity research and portfolio analysis.

## Overview

This project contains **two distinct but related systems** using a **skills-based architecture** where each skill is a standalone executable Python script:

1. **Stock Research Skills** - Automated equity research report generation using multi-phase data gathering and AI-powered analysis
2. **Portfolio Management Skills** - Fidelity portfolio aggregation, categorization, and visualization tools

All skills can be run independently or orchestrated together for complex workflows.

## Quick Start

### Stock Research
```bash
# Complete research for a stock (all phases)
./skills/research_stock.py TSLA

# Run specific phases only
./skills/research_stock.py TSLA --phases technical,fundamental,report

# With custom peer companies
./skills/research_stock.py TSLA --peers "GM,F,TM,RIVN"
```

### Portfolio Management
```bash
# 1. Export CSV files from Fidelity and place them in import/
# 2. Run aggregation skill
./skills/aggregate_positions.py

# 3. Update security mappings if needed
# Edit data/security_mapping.csv to categorize securities

# 4. Generate visualization
./skills/visualize_allocation.py
```

## Project Structure

```
mcpskills/
├── work/                # Stock research outputs
│   └── {SYMBOL}_{YYYYMMDD}/  # Per-stock research directories
│       ├── 00_metadata.json
│       ├── 01_technical/
│       ├── 02_fundamental/
│       ├── 03_research/
│       ├── 04_sec/
│       ├── 05_wikipedia/
│       ├── 06_analysis/
│       ├── 08_deep_research/
│       ├── research_report.md
│       ├── final_report.md
│       ├── final_report.docx
│       └── final_report.html
├── import/              # Fidelity CSV exports (Portfolio_Positions_*.csv)
├── data/                # Aggregated portfolio data and mappings
│   ├── aggregate_positions.csv
│   ├── aggregate_positions_YYYYMMDD.csv
│   └── security_mapping.csv
├── dataviz/             # Interactive portfolio visualizations
│   └── allocation_sunburst_YYYYMMDD.html
├── skills/              # All executable skills
│   ├── research_stock.py          # Research orchestrator
│   ├── lookup_ticker.py
│   ├── research_technical.py
│   ├── research_fundamental.py
│   ├── research_perplexity.py
│   ├── research_sec.py
│   ├── research_wikipedia.py
│   ├── research_analysis.py
│   ├── research_report.py
│   ├── research_deep.py
│   ├── research_final.py
│   ├── filter_peers.py
│   ├── aggregate_positions.py
│   ├── visualize_allocation.py
│   └── README.md                  # Detailed skill documentation
├── templates/           # Jinja2 report templates
│   ├── equity_research_report.md.j2
│   ├── analyst_report.md.j2
│   └── final_report.md.j2
├── CLAUDE.md            # Instructions for Claude Code
├── EQUITY_RESEARCH_PROCESS.md  # Research workflow documentation
└── README.md            # This file
```

## Stock Research Skills

### Research Workflow

The stock research system uses a **multi-phase pipeline** orchestrated by `research_stock.py` that executes in two stages:

**Stage 1: Data Gathering (Parallel)** - Technical, fundamental, research, analysis, SEC, and Wikipedia phases run concurrently

**Stage 2: Report Generation (Sequential)** - Report synthesis, deep research, and final assembly phases run in order

### Core Orchestrator

**research_stock.py** - Main orchestrator coordinating the entire research workflow

```bash
# Complete research with all phases
./skills/research_stock.py TSLA

# Run specific phases
./skills/research_stock.py INTC --phases technical,fundamental,research,report

# With custom peer companies
./skills/research_stock.py TSLA --peers "GM,F,TM,RIVN"

# Keep old directories (don't cleanup)
./skills/research_stock.py AAPL --skip-cleanup
```

**Process:**
1. Validates ticker symbol
2. Creates `work/{SYMBOL}_{YYYYMMDD}` directory
3. Executes data gathering phases in parallel (max 6 workers)
4. Executes report generation phases sequentially
5. Outputs comprehensive research report in multiple formats

### Research Phase Skills

Each phase is a standalone skill that can be run independently:

#### 1. lookup_ticker.py
Ticker symbol lookup and validation using OpenBB API.

```bash
./skills/lookup_ticker.py "Tesla"
./skills/lookup_ticker.py "Broadcom" --limit 5 --save
```

#### 2. research_technical.py
Technical analysis phase - generates charts and calculates technical indicators.

**Output:** `01_technical/`
- `chart.png` - 4-year weekly candlestick chart with MA13, MA52, volume, relative strength
- `technical_analysis.json` - Technical indicators (SMA, RSI, MACD, ATR, Bollinger Bands)
- `peers_list.json` - Identified peer companies

#### 3. research_fundamental.py
Fundamental analysis phase - gathers financial data and company fundamentals.

**Output:** `02_fundamental/`
- `company_overview.json` - Company profile, market data, valuation metrics
- `income_statement.csv` - Historical income statements
- `balance_sheet.csv` - Historical balance sheets
- `cash_flow.csv` - Historical cash flow statements
- `key_ratios.csv` - 5-year financial ratios (from OpenBB/FMP)
- `analyst_recommendations.json` - Analyst ratings and price targets
- `news.json` - Recent news articles

#### 4. research_perplexity.py
Perplexity AI research phase - deep research using AI for qualitative analysis.

**Output:** `03_research/`
- `news_stories.md` - Major news since 2024 (10-15 stories with sources)
- `business_profile.md` - 10-section comprehensive business analysis
- `executive_profiles.md` - C-suite profiles and backgrounds

#### 5. research_sec.py
SEC filings research phase - downloads and parses official 10-K filings.

**Output:** `04_sec/`
- `10k_item1.txt` - Item 1 (Business Description) from latest 10-K
- `10k_metadata.json` - Filing metadata

#### 6. research_wikipedia.py
Wikipedia research phase - fetches company information.

**Output:** `05_wikipedia/`
- `wikipedia_summary.txt` - Wikipedia page summary
- `wikipedia_metadata.json` - Page metadata

#### 7. research_analysis.py
Deep analysis phase - generates analytical insights using Perplexity AI.

**Output:** `06_analysis/`
- `business_model_analysis.md` - 5-section deep dive on business model
- `competitive_analysis.md` - Competitive landscape and dynamics
- `risk_analysis.md` - Recent news, analyst reports, legal/regulatory issues
- `investment_thesis.md` - SWOT, bull/bear cases, critical watch points

#### 8. research_report.py
Report generation phase - assembles comprehensive analyst-style research report.

**Output:**
- `research_report.md` - Comprehensive markdown research report synthesizing all phase data

#### 9. research_deep.py
Deep research phase - comprehensive analysis using Claude Agent SDK with MCP tools.

**Output:** `08_deep_research/`
- `deep_research_output.md` - 9-section comprehensive analysis (~10K-20K characters)
- `deep_research_thinking.md` - Extended thinking process from Claude
- `tool_usage.txt` - Log of MCP tools used during research

**Features:**
- Uses Claude Sonnet 4.5 with extended thinking (10K token budget)
- Access to 6 MCP servers for real-time data gathering (stock-symbol-server, alphavantage, yfinance, brave-search, perplexity-ask, wikipedia)
- Hybrid mode: receives research_report.md as context, uses MCP tools to fill gaps
- Execution time: 2-5 minutes with tools, cost ~$1-2 per run

**Report Sections:**
1. Short Summary Overall Assessment
2. Extended Profile (history, core business, recent news)
3. Business Model (revenue streams, customer segments, competitive advantages)
4. Competitive Landscape (competitors, market share, differentiation)
5. Supply Chain Positioning
6. Financial & Operating Leverage
7. Valuation (methodologies, multiples, analyst opinions)
8. Recent Developments & Risk Factors
9. Conclusion (SWOT, bull/bear cases, watch points)

#### 10. research_final.py
Final report assembly phase - combines all research into polished final report with multi-format export.

**Output:**
- `final_report.md` - Final polished markdown report
- `final_report.docx` - Word document (if pandoc or python-docx available)
- `final_report.html` - Standalone HTML report (if pandoc or markdown available)

**Report Structure:**
1. Executive Summary
2. Stock Chart (4-year weekly with technical indicators)
3. Technical Analysis Summary (key indicators table, trend signals)
4. Peer Comparison (enhanced 8-column table with financial metrics)
5. Comprehensive Deep Research Analysis (full 9-section analysis)
6. Investment Conclusion (strategic position, SWOT, watch points)

#### 11. filter_peers.py
Peer filtering utility - filters and ranks peer companies based on relevance criteria.

### Supporting Library

**agent_tools.py** - Data loading library for agent-based workflows (not a standalone skill). Provides simple functions for loading research data from work directories.

---

## Portfolio Management Skills

### Available Skills

#### 1. aggregate_positions.py

Consolidates positions from multiple Fidelity accounts into a single aggregated view.

```bash
./skills/aggregate_positions.py
```

**Features:**
- Combines 5 account types (Individual-TOD, ROTH IRA, Rollover IRA, SEP-IRA, Traditional IRA)
- Normalizes cash positions (FDRXX**, Pending Activity → Cash)
- Handles short positions correctly (negative values)
- Creates dated archives automatically
- Calculates weighted average cost basis

**Output:**
- `data/aggregate_positions.csv` (current)
- `data/aggregate_positions_YYYYMMDD.csv` (archive)

#### 2. visualize_allocation.py

Creates interactive sunburst chart showing hierarchical allocation.

```bash
./skills/visualize_allocation.py
```

**Features:**
- 4-level drill-down: L1 (Economic Factor) → L2 (Region/Asset Class) → L3 (Sub-category) → L4 (Specific) → Symbol
- Interactive hover details (value, percentage, quantity, price)
- Color-coded by L1 category (GROWTH/DEFLATION/INFLATION/CASH)
- Standalone HTML (no server required)
- Handles negative positions (short sales)

**Output:**
- `dataviz/allocation_sunburst_YYYYMMDD.html`

## Category Hierarchy

Portfolio positions are categorized using an economic factor-based framework:

**L1: Economic Factors**
- **GROWTH** - Assets that grow with economic expansion (stocks, equity funds)
- **DEFLATION** - Assets that perform well in deflation (treasuries, preferred stocks)
- **INFLATION** - Assets that protect against inflation (TIPS)
- **CASH** - Liquid reserves and money market positions

**Example Hierarchy:**
```
GROWTH
├── US
│   ├── LARGECAP → OAKMX
│   ├── SMALLCAP → FTHSX
│   └── INDIVIDUAL → INTC, TSLA
├── INTERNATIONAL
│   ├── DEVELOPED → OAKIX
│   ├── EMERGINGMARKETS → FDEM
│   └── CHINA → KWEB
└── SPECIAL
    ├── CLEANENERGY → GRID
    └── INFRASTRUCTURE → SRVR

DEFLATION
├── TREASURY
│   ├── INTERMEDIATE → VGIT
│   └── LONGTERM → VGLT
└── PREFERRED
    ├── BANKS → BACPRB, JPMPRC
    ├── INSURANCE → METPRE
    └── FINANCIAL → SCHWPRD

INFLATION
└── TIPS
    ├── SHORT → VTIP
    └── BROAD → TIP, VIPSX

CASH
└── Cash (money market, pending activity)
```

### Planned Portfolio Skills

Future skills for portfolio restructuring:

#### 3. analyze_allocation.py
Compare actual vs target allocations, identify rebalancing needs

#### 4. optimize_rebalance.py
Generate optimal trade orders to reach target allocation

#### 5. analyze_trends.py
Track allocation changes over time using archived snapshots

#### 6. analyze_risk.py
Analyze portfolio risk metrics and concentration

#### 7. track_performance.py
Calculate returns and compare to benchmarks

## Configuration Files

### security_mapping.csv
Maps each security symbol to its category hierarchy:

```csv
Symbol,L1,L2,L3,L4
OAKMX,GROWTH,US,LARGECAP,
VGIT,DEFLATION,TREASURY,INTERMEDIATE,
VTIP,INFLATION,TIPS,SHORT,
Cash,CASH,,,
```

**Maintenance:**
- Add new row when purchasing new security
- Update categories if security changes character
- L1 values must be: GROWTH, DEFLATION, INFLATION, or CASH
- L2-L4 are optional but help with organization

### target_allocation.csv (future)
Will define target allocation percentages:

```csv
Category,Target_Pct
GROWTH,50.0
DEFLATION,25.0
INFLATION,25.0
CASH,0.0
```

## Development

### Python Environment

This project requires **Python 3.11** (for OpenBB compatibility). Use conda for environment management:

```bash
# Activate conda environment
conda activate fidelity

# Install dependencies
pip install -r requirements.txt

# TA-Lib requires system library (macOS)
brew install ta-lib
export TA_INCLUDE_PATH="$(brew --prefix ta-lib)/include"
export TA_LIBRARY_PATH="$(brew --prefix ta-lib)/lib"
pip install TA-Lib

# Optional: Install pandoc for document conversion
brew install pandoc
```

### Required API Keys

Set these in `.env` file in project root:

```bash
# OpenBB Platform (for ticker lookup and financial ratios)
OPENBB_PAT=your_openbb_pat_here

# Perplexity AI (for qualitative research and analysis phases)
PERPLEXITY_API_KEY=your_perplexity_key_here

# Anthropic API (for deep research phase with Claude Sonnet 4.5)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: SEC API identifiers
SEC_FIRM=your_firm_name
SEC_USER=your_email@example.com
```

### Dependencies

**Core (Both Systems):**
- Python 3.11+
- pandas >= 2.0
- python-dotenv

**Stock Research - Data Gathering:**
- yfinance (stock data and fundamentals)
- openbb (OpenBB Platform for financial data)
- numpy
- plotly >= 5.0 (for chart generation)
- talib (TA-Lib for technical indicators)
- openai (for Perplexity API - OpenAI-compatible)
- sec-edgar-downloader (for SEC filings)
- beautifulsoup4 (for HTML parsing)
- wikipediaapi (for Wikipedia data)

**Stock Research - Report Generation:**
- jinja2 (for report templating)
- anthropic (for Claude API access)
- claude-agent-sdk (for MCP server integration in deep research)
- mcp (Model Context Protocol)
- python-docx (optional, for Word document generation)
- lxml (for XML/HTML parsing)
- markdown (optional, for HTML report generation)

**Portfolio Management:**
- plotly >= 5.0 (for visualizations)

### MCP Server Configuration

The deep research phase (`research_deep.py`) can use MCP servers for real-time data access. Configure in `~/Library/Application Support/Claude/claude_desktop_config.json`:

Supported servers:
- `stock-symbol-server` - Local server.py with financial tools
- `alphavantage` - Alpha Vantage financial data
- `yfinance` - Yahoo Finance data
- `brave-search` - Web search
- `perplexity-ask` - AI-powered search
- `wikipedia` - Company information

See CLAUDE.md for details on MCP server setup.

### Creating New Skills

Skills should follow these conventions:

1. **Shebang:** `#!/opt/anaconda3/envs/fidelity/bin/python3`
2. **Executable:** `chmod +x skills/your_skill.py`
3. **Docstring:** Include usage instructions at top of file
4. **Arguments:** Use argparse for directory paths and options
5. **Error Handling:** Graceful failures with helpful messages
6. **Output:** Create directories as needed, use dated archives
7. **Documentation:** Update `skills/README.md` with skill details
8. **Return codes:** Return 0 for success, 1 for failure

## Workflows

### Stock Research Workflow

Complete equity research for a stock:

1. **Run the orchestrator** to execute all phases
   ```bash
   ./skills/research_stock.py TSLA
   ```

2. **Review outputs** in `work/TSLA_YYYYMMDD/`
   - Check phase directories for gathered data
   - Review `research_report.md` for initial synthesis
   - Review `final_report.md` for polished analysis

3. **View reports** in multiple formats
   - Open `final_report.html` in browser for interactive viewing
   - Open `final_report.docx` in Word for editing/sharing
   - Read `final_report.md` for markdown format

4. **Optional: Run specific phases independently**
   ```bash
   # Update just the report with a different template
   ./skills/research_report.py TSLA --work-dir work/TSLA_20251220 --template analyst_report.md.j2

   # Re-run deep research
   ./skills/research_deep.py TSLA --work-dir work/TSLA_20251220

   # Regenerate final report
   ./skills/research_final.py TSLA --work-dir work/TSLA_20251220
   ```

### Portfolio Management Workflow

Regular portfolio review:

1. **Export data from Fidelity** (weekly/monthly)
   - Download CSV for each account
   - Place files in `import/`

2. **Aggregate positions**
   ```bash
   ./skills/aggregate_positions.py
   ```

3. **Update mappings** (if new securities purchased)
   - Edit `data/security_mapping.csv`
   - Add new rows for new symbols

4. **Generate visualization**
   ```bash
   ./skills/visualize_allocation.py
   ```

5. **Review allocation**
   - Open `dataviz/allocation_sunburst_YYYYMMDD.html` in browser
   - Drill down through categories
   - Identify areas needing rebalancing

### Portfolio Restructuring

When rebalancing or restructuring:

1. Run allocation analysis to identify needs (future skill)
2. Use optimizer to generate trade recommendations (future skill)
3. Review trades for tax implications
4. Execute trades in Fidelity
5. Export new CSV files and re-aggregate
6. Generate new visualization to confirm changes

## Special Cases

### Short Positions
Short positions (e.g., TSLA short) are handled correctly with negative values:
- Quantity is negative
- Value is negative
- Reduces category total appropriately
- Visualization uses absolute value for sizing but displays actual value

### Cash Positions
Multiple cash representations are normalized:
- `FDRXX**` (Fidelity money market) → Cash
- `Pending Activity` → Cash
- `Cash` → Cash
- Quantity is set equal to current value for cash positions

### Multiple Accounts
Positions are aggregated across all account types:
- Same symbol in different accounts are summed
- Cost basis is averaged by total cost / total quantity
- Position type uses first non-null value

## Cost Considerations

### Stock Research Costs

API usage costs per stock research run (all phases):

- **Perplexity AI** (~$0.36 per stock)
  - research_perplexity.py: ~18K tokens (3 queries)
  - research_analysis.py: ~18K tokens (4 queries)
  - Total: ~36K tokens @ $0.01/1K tokens

- **Anthropic Claude API** (~$1-2 per stock with deep research)
  - research_deep.py with MCP tools: ~$1-2
  - Basic mode (no tools): ~$0.50-1

**Cost optimization tips:**
- Skip `analysis` phase for quick research (saves ~$0.18)
- Skip `deep` phase to use template-based reports only (saves ~$1-2)
- Use `--phases` flag to run only needed phases

### Portfolio Management Costs

No API costs - all portfolio skills run locally with free data sources.

## File Locations

**Stock Research:**
- **Skills:** `skills/research_*.py` - Research phase scripts
- **Templates:** `templates/*.md.j2` - Jinja2 report templates
- **Work Output:** `work/{SYMBOL}_{YYYYMMDD}/` - Per-stock research directories

**Portfolio Management:**
- **Skills:** `skills/aggregate_positions.py`, `skills/visualize_allocation.py`
- **Data:** `data/` - Aggregated positions and mappings
- **Visualizations:** `dataviz/` - Interactive HTML charts
- **Import:** `import/` - Fidelity CSV exports

**Documentation:**
- **skills/README.md** - Comprehensive skill documentation (1000+ lines)
- **CLAUDE.md** - Instructions for Claude Code
- **EQUITY_RESEARCH_PROCESS.md** - Detailed research workflow
- **spec.md** - Portfolio skills development plan

## Important Notes

**Stock Research:**
- All skills are executable: `chmod +x skills/*.py`
- Working directory auto-set to script location on startup
- Older work directories deleted by default (use `--skip-cleanup` to preserve)
- Report generation works with partial data if phases fail
- Deep research phase requires claude-agent-sdk and configured MCP servers
- Multi-format export requires pandoc (preferred) or python libraries (fallback)

**Portfolio Management:**
- Cash positions automatically normalized (FDRXX**, Pending Activity → Cash)
- Short positions handled correctly with negative values
- Cost basis weighted by total cost / total quantity across accounts

## Related Files

See also:
- **skills/README.md** - Detailed documentation of all skills (1000+ lines)
- **CLAUDE.md** - Development guide for Claude Code
- **EQUITY_RESEARCH_PROCESS.md** - Research workflow and best practices

## License

This is a personal research and portfolio management tool. No license specified.

## Support

For detailed documentation of each skill's functionality and usage, see **skills/README.md** which provides comprehensive documentation including:
- Detailed usage instructions for each skill
- Input/output specifications
- Data sources and API requirements
- Feature descriptions and capabilities
- Example outputs and workflows
