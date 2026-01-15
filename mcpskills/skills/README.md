# Research and Portfolio Skills

This directory contains standalone skills for portfolio analysis and securities research.

## Overview

Skills are organized into two categories:
1. **Portfolio Management Skills** - Aggregate and visualize your Fidelity portfolio positions
2. **Securities Research Skills** - Research individual securities with comprehensive data gathering and analysis

All skills follow a consistent architecture:
- Standalone executable Python scripts (`#!/opt/anaconda3/envs/mcpskills/bin/python3`)
- Command-line arguments via argparse
- Self-contained with comprehensive error handling
- Create output directories as needed

## Portfolio Management Skills

### 1. aggregate_positions.py

Aggregates Fidelity portfolio positions from multiple CSV exports into a single consolidated file.

**Purpose:**
- Consolidate positions across multiple accounts (Individual, ROTH IRA, Rollover IRA, SEP-IRA, Traditional IRA)
- Create archival snapshots of portfolio state
- Prepare data for further analysis and categorization

**Usage:**
```bash
# From project root directory (uses default directories)
./skills/aggregate_positions.py

# Or with custom directories
./skills/aggregate_positions.py --import-dir import --output-dir data

# Or with explicit python
/opt/anaconda3/envs/mcpskills/bin/python3 skills/aggregate_positions.py
```

**Arguments:**
- `--import-dir DIR`: Directory containing Fidelity CSV exports (default: `./import`)
- `--output-dir DIR`: Directory for output files (default: `./data`)

**Input:**
- CSV files exported from Fidelity accounts
- Expected format: `Portfolio_Positions_*.csv`
- Files should contain columns: Symbol, Description, Quantity, Last Price, Current Value, Cost Basis Total, Type

**Output:**
- `data/aggregate_positions.csv`: Current aggregated positions (overwrites on each run)
- `data/aggregate_positions_YYYYMMDD.csv`: Dated archive (e.g., `aggregate_positions_20251213.csv`)
- Creates `data/` directory automatically if it doesn't exist

**Output Format:**
```csv
symbol,description,quantity,last_price,value,average_cost_basis,total_cost_basis,type
Cash,Cash,785569.38,,785569.38,,0.00,Cash
OAKMX,OAKMARK FUND INVESTOR CLASS,649.23,173.64,112732.12,50.48,32770.54,Margin
...
```

**Special Handling:**
- Cash positions: Aggregates FDRXX**, Pending Activity, and Cash into single "Cash" position
- Short positions: Maintains negative values (e.g., TSLA short)
- Cost basis: Calculates weighted average from aggregated totals
- Multiple accounts: Sums quantities and values across all accounts

**Example Output:**
```
============================================================
Fidelity Portfolio Aggregation
============================================================
Reading CSV files from: import
Found 5 CSV file(s)
  - Loaded: Portfolio_Positions_Dec-12-2025.csv (4 rows)
  - Loaded: Portfolio_Positions_Dec-12-2025 (1).csv (10 rows)
  ...

Combined data: 39 total rows
Aggregated to 19 unique positions
Total portfolio value: $1,441,789.58

✓ Saved current positions to: data/aggregate_positions.csv
✓ Saved archive to: data/aggregate_positions_20251213.csv
```

## Workflow

The typical workflow for using these skills:

1. **Export Data from Fidelity**
   - Download CSV files for each account
   - Place all CSV files in the `import/` directory

2. **Aggregate Positions**
   ```bash
   ./skills/aggregate_positions.py
   ```
   - Creates `data/` directory if needed
   - Creates `data/aggregate_positions.csv` with current data
   - Creates dated archive `data/aggregate_positions_YYYYMMDD.csv`

3. **Create/Update Security Mapping**
   - Edit `data/security_mapping.csv` to map securities to categories
   - Define L1 (GROWTH/DEFLATION/INFLATION/CASH) through L4 hierarchy
   - Add new securities as they're purchased

4. **Visualize Allocation**
   ```bash
   ./skills/visualize_allocation.py
   ```
   - Creates `dataviz/` directory if needed
   - Generates interactive sunburst chart
   - Open `dataviz/allocation_sunburst_YYYYMMDD.html` in browser

5. **Further Analysis** (planned)
   - Compare against target allocations
   - Generate rebalancing recommendations
   - Analyze historical trends

### 2. visualize_allocation.py

Creates interactive HTML sunburst chart showing portfolio allocation by category hierarchy.

**Purpose:**
- Visualize portfolio allocation across the 4-level category hierarchy
- Enable drill-down navigation through categories (L1 → L2 → L3 → L4 → Symbol)
- Provide detailed position information on hover
- Generate standalone HTML files viewable in any browser

**Usage:**
```bash
# From project root directory (uses default directories)
./skills/visualize_allocation.py

# Or with custom directories
./skills/visualize_allocation.py --data-dir data --output-dir dataviz

# Or with explicit python
/opt/anaconda3/envs/mcpskills/bin/python3 skills/visualize_allocation.py
```

**Arguments:**
- `--data-dir DIR`: Directory containing data files (default: `./data`)
- `--output-dir DIR`: Directory for output visualizations (default: `./dataviz`)

**Input:**
- `data/aggregate_positions.csv`: Aggregated portfolio positions
- `data/security_mapping.csv`: Symbol-to-category mappings

**Output:**
- `dataviz/allocation_sunburst_YYYYMMDD.html`: Interactive sunburst chart
- Creates `dataviz/` directory automatically if it doesn't exist

**Features:**
- **Interactive Drill-Down**: Click any category or security to zoom in/out
- **Hierarchical View**: Navigate through L1 (GROWTH/DEFLATION/INFLATION/CASH) → L2 (US/INTERNATIONAL/TREASURY/etc) → L3 → L4 → Symbol
- **Hover Information**:
  - Security name/category
  - Current value (with proper handling of short positions)
  - Percentage of total portfolio
  - Quantity and last price (for individual securities)
  - Position type (Cash, Margin, Short)
  - Description
- **Visual Design**:
  - Color-coded segments for easy identification
  - Percentage labels on each segment
  - Responsive sizing (1200x800px default)
  - Clean white borders between segments

**Example Output:**
```
============================================================
Fidelity Portfolio Visualization
============================================================
Loading data from: data
  ✓ Loaded 19 positions
  ✓ Loaded 20 security mappings

✓ Prepared 19 securities for visualization
  Total portfolio value: $1,441,789.58

Building hierarchical structure...

✓ Saved visualization to: dataviz/allocation_sunburst_20251213.html

============================================================
SUCCESS: Visualization created!
============================================================

Open in browser: dataviz/allocation_sunburst_20251213.html
```

**Special Handling:**
- Short positions: Uses absolute value for sizing, displays actual (negative) value on hover
- Unmapped securities: Warns about unmapped symbols but continues with mapped positions
- Empty categories: Only displays categories that contain positions

---

## Securities Research Skills

The securities research skills perform comprehensive equity research on individual stocks, gathering data from multiple sources and generating analyst-style reports.

### Research Workflow

The typical research workflow uses the orchestrator skill which executes phases in three stages:

**Stage 1: Technical Analysis (Sequential)** - Technical phase runs first to generate peer list

**Stage 2: Data Gathering (Parallel)** - Fundamental, research, analysis, SEC, and Wikipedia phases run concurrently (using peer list from Stage 1)

**Stage 3: Report Generation (Sequential)** - Report, deep research, and final assembly phases run in order

**IMPORTANT DEPENDENCY:** Technical phase must run before fundamental phase, as fundamental needs the peer list generated by technical for peer comparison analysis.

```bash
# Run complete research workflow for a stock
./skills/research_stock.py TSLA

# Run with custom peer companies
./skills/research_stock.py TSLA --peers "GM,F,TM,RIVN"

# Run specific phases only
./skills/research_stock.py INTC --phases technical,fundamental,report

# Run without cleaning up old directories
./skills/research_stock.py AAPL --skip-cleanup
```

**Output Structure:**
Each research run creates a work directory: `work/{SYMBOL}_{YYYYMMDD}/`

```
work/TSLA_20251220/
├── 00_metadata.json              # Research metadata and phase tracking
├── 01_technical/                 # Technical analysis phase
│   ├── chart.png
│   ├── technical_analysis.json
│   └── peers_list.json
├── 02_fundamental/               # Fundamental data phase
│   ├── company_overview.json
│   ├── income_statement.csv
│   ├── balance_sheet.csv
│   ├── cash_flow.csv
│   ├── key_ratios.csv
│   ├── analyst_recommendations.json
│   └── news.json
├── 03_research/                  # Perplexity AI research phase
│   ├── news_stories.md
│   ├── business_profile.md
│   └── executive_profiles.md
├── 04_sec/                       # SEC filings phase
│   ├── 10k_item1.txt
│   └── 10k_metadata.json
├── 05_wikipedia/                 # Wikipedia research phase
│   ├── wikipedia_summary.txt
│   └── wikipedia_metadata.json
├── 06_analysis/                  # Deep analysis phase
│   ├── business_model_analysis.md
│   ├── competitive_analysis.md
│   ├── risk_analysis.md
│   └── investment_thesis.md
├── 08_deep_research/             # Claude Agent SDK deep research phase
│   ├── deep_research_output.md
│   ├── deep_research_thinking.md
│   └── tool_usage.txt
├── research_report.md            # Intermediate comprehensive report
├── final_report.md               # Final polished report
├── final_report.docx             # Word document (if pandoc available)
└── final_report.html             # HTML report (if pandoc/markdown available)
```

### Core Orchestrator

#### 1. research_stock.py

**Main orchestrator** that coordinates the entire research workflow across multiple phases.

**Purpose:**
- Validate ticker symbols
- Create and manage work directories
- Execute research phases in parallel (6 concurrent workers)
- Track phase completion and errors
- Cleanup old research directories

**Usage:**
```bash
# Complete research with all phases
./skills/research_stock.py TSLA

# Run specific phases
./skills/research_stock.py INTC --phases technical,fundamental,research

# Keep old directories
./skills/research_stock.py AAPL --skip-cleanup
```

**Arguments:**
- `symbol`: Stock ticker symbol (e.g., TSLA, AAPL, MSFT)
- `--phases`: Comma-separated list of phases (default: all)
  - Available: `technical`, `fundamental`, `research`, `analysis`, `sec`, `wikipedia`, `report`, `deep`, `final`
- `--peers`: Comma-separated custom peer ticker symbols (e.g., "GM,F,TM")
- `--skip-cleanup`: Don't delete old work directories for this symbol

**Process:**
1. Validates ticker using lookup_ticker.py
2. Creates `work/{SYMBOL}_{YYYYMMDD}` directory
3. Cleans up old directories (unless --skip-cleanup)
4. **Stage 1:** Executes technical phase sequentially (generates peer list)
   - technical (charts, indicators, peer identification)
5. **Stage 2:** Executes remaining data gathering phases in parallel (max 6 workers)
   - fundamental (uses peer list from technical), research, analysis, sec, wikipedia
6. **Stage 3:** Executes report generation phases sequentially
   - report (synthesizes data into research_report.md)
   - deep (Claude Agent SDK with MCP tools for deep analysis)
   - final (assembles final_report with multi-format export)
7. Tracks success/failure of each phase

**Example Output:**
```
============================================================
Stock Research Orchestrator
============================================================
Symbol: TSLA
Phases: all
Date: 2025-12-20 14:30:00
============================================================

Step 1: Ticker Validation
✓ Ticker 'TSLA' validated

Step 2: Work Directory Setup
✓ Created work directory: work/TSLA_20251220
✓ No old directories to clean up

Step 3: Execute Research Phases
Executing 6 data phases in parallel...

[Phases run concurrently with real-time output]

✓ Phase 'technical' completed successfully
✓ Phase 'fundamental' completed successfully
...

Generating report from collected data...
✓ Phase 'report' completed successfully

============================================================
Research Complete
============================================================
Phases completed: 7
Phases failed: 0
✓ See outputs in: work/TSLA_20251220
```

### Individual Research Phase Skills

Each phase can also be run independently for development or debugging:

#### 2. lookup_ticker.py

**Ticker symbol lookup and validation** with multi-provider fallback (yfinance → Finnhub → OpenBB+FMP).

**Purpose:**
- Search for ticker symbols by company name
- Validate ticker symbols before research
- Find correct tickers when uncertain
- Automatic fallback to multiple data sources

**Usage:**
```bash
# Search for a company (tries yfinance, then Finnhub, then OpenBB)
./skills/lookup_ticker.py "Broadcom"

# Validate a symbol
./skills/lookup_ticker.py "AVGO"

# Limit results
./skills/lookup_ticker.py "Apple Inc" --limit 5

# Save results to CSV
./skills/lookup_ticker.py "Tesla" --save
```

**Arguments:**
- `query`: Company name or ticker symbol
- `--provider`: OpenBB data provider (only used as fallback, default: cboe)
- `--limit`: Maximum results (default: 10)
- `--save`: Save results to CSV in data/ directory

**Environment (prioritized fallback):**
- `FINNHUB_API_KEY` - Recommended (free tier, get at https://finnhub.io/register)
- `OPENBB_PAT` - Optional fallback (set in .env)

**Output:**
- Prints matching tickers with exchange, name, type
- Shows which provider was used (yfinance, Finnhub, or OpenBB+FMP)
- Optionally saves to `data/ticker_search_{timestamp}.csv`

#### 3. research_technical.py

**Technical analysis phase** - generates charts and calculates technical indicators.

**Purpose:**
- Create weekly stock charts with moving averages
- Calculate technical indicators (RSI, MACD, ATR, Bollinger Bands)
- Analyze trend signals and momentum
- Identify peer companies

**Usage:**
```bash
# Auto-infer work directory from symbol and date
./skills/research_technical.py TSLA

# Specify custom work directory
./skills/research_technical.py TSLA --work-dir work/TSLA_20251220

# Specify custom peer companies
./skills/research_technical.py TSLA --peers "GM,F,TM,RIVN"
```

**Arguments:**
- `symbol`: Stock ticker symbol
- `--work-dir`: Work directory path (default: work/SYMBOL_YYYYMMDD)
- `--peers`: Comma-separated custom peer ticker symbols (overrides auto-detection)

**Output:**
- `01_technical/chart.png` - Weekly candlestick chart with MA13, MA52, volume, relative strength vs S&P 500
- `01_technical/technical_analysis.json` - Technical indicators and trend signals
- `01_technical/peers_list.json` - List of peer companies

**Technical Indicators Calculated:**
- **Moving Averages:** SMA 20, 50, 200
- **Momentum:** RSI (14-period), MACD (12, 26, 9)
- **Volatility:** ATR (14-period), Bollinger Bands (20, 2σ)
- **Trend Signals:** Price vs SMAs, SMA crossovers, MACD signals

**Data Sources:**
- yfinance for price data and peer enrichment
- TA-Lib for technical indicators
- Finnhub → OpenBB+FMP for peer company detection (automatic fallback)
- Plotly for chart generation

#### 4. research_fundamental.py

**Fundamental analysis phase** - gathers financial data and company fundamentals.

**Purpose:**
- Collect comprehensive company financial data
- Get financial statements (income, balance sheet, cash flow)
- Calculate financial ratios
- Gather analyst recommendations

**Usage:**
```bash
# Auto-infer work directory from symbol and date
./skills/research_fundamental.py TSLA

# Specify custom work directory
./skills/research_fundamental.py TSLA --work-dir work/TSLA_20251220
```

**Arguments:**
- `symbol`: Stock ticker symbol
- `--work-dir`: Work directory path (default: work/SYMBOL_YYYYMMDD)

**Output (02_fundamental/):**
- `company_overview.json` - Company info, financial metrics, valuation ratios
- `income_statement.csv` - Historical income statements
- `balance_sheet.csv` - Historical balance sheets
- `cash_flow.csv` - Historical cash flow statements
- `key_ratios.csv` - Financial ratios (5-year history from OpenBB/FMP)
- `analyst_recommendations.json` - Recent analyst ratings and price targets
- `news.json` - Recent news articles

**Key Metrics Captured:**
- Company profile (sector, industry, employees, website)
- Market data (market cap, enterprise value, beta, 52-week range)
- Valuation (P/E, P/B, P/S, PEG ratio)
- Profitability (margins, ROE, ROA, EPS)
- Growth (revenue growth, quarterly trends)
- Shareholder info (shares outstanding, short interest, insider/institutional holdings)

**Data Sources:**
- yfinance for company info, statements, and all financial data

#### 5. research_perplexity.py

**Perplexity AI research phase** - deep research using AI for qualitative analysis.

**Purpose:**
- Research major news stories and developments
- Analyze business model and competitive positioning
- Profile executive leadership

**Usage:**
```bash
./skills/research_perplexity.py TSLA --work-dir work/TSLA_20251220
```

**Arguments:**
- `symbol`: Stock ticker symbol
- `--work-dir`: Work directory path (required)

**Output (03_research/):**
- `news_stories.md` - Major news since 2024 (10-15 stories, chronological, with sources)
- `business_profile.md` - Comprehensive 10-section business analysis
- `executive_profiles.md` - C-suite executive profiles and backgrounds

**News Stories Coverage:**
- Top-tier financial media sources (WSJ, Bloomberg, FT, Reuters, CNBC)
- Corporate developments (earnings, launches, M&A, partnerships)
- Regulatory issues and investigations
- Leadership changes
- Market-moving events

**Business Profile Sections:**
1. Company History & Evolution
2. Business Model & Revenue Streams
3. Competitive Advantages & Moats
4. Market Position & Share
5. Supply Chain Positioning
6. Financial Health Overview
7. Growth Strategy
8. Risk Factors
9. Industry Trends
10. Recent Developments (6-12 months)

**Executive Profiles Include:**
- Name, title, background, education
- Compensation (if public)
- Tenure and achievements
- Recent strategic statements
- Any controversies

**Environment:**
- Requires `PERPLEXITY_API_KEY` environment variable

**Features:**
- Automatic retry logic with exponential backoff
- Uses sonar-pro model for high-quality research
- Temperature 0.2 for factual accuracy
- 4000-8000 token responses for comprehensive coverage

#### 6. research_sec.py

**SEC filings research phase** - downloads and parses official SEC 10-K filings.

**Purpose:**
- Download latest 10-K filing from SEC EDGAR
- Extract Item 1 (Business Description)
- Provide official business description from regulatory filing

**Usage:**
```bash
./skills/research_sec.py TSLA --work-dir work/TSLA_20251220
```

**Arguments:**
- `symbol`: Stock ticker symbol
- `--work-dir`: Work directory path (required)

**Output (04_sec/):**
- `10k_item1.txt` - Item 1 (Business) section from latest 10-K (~50K-100K characters)
- `10k_metadata.json` - Filing metadata (date, filing path, length)

**What is Item 1?**
Item 1 of the 10-K contains the official business description including:
- Nature of business and principal products/services
- Competitive conditions and market positioning
- Raw materials and supply chain
- Patents, trademarks, and intellectual property
- Seasonality
- Working capital practices
- Customer and geographic concentrations
- Regulatory environment

**Features:**
- Automatic parsing to extract Item 1 section
- Falls back to full filing if parsing fails
- Cleans up temporary download files

**Data Source:**
- SEC EDGAR database via sec-edgar-downloader

#### 7. research_wikipedia.py

**Wikipedia research phase** - fetches company information from Wikipedia.

**Purpose:**
- Get company history and background
- Provide accessible, general-audience overview
- Supplement official sources with contextual information

**Usage:**
```bash
./skills/research_wikipedia.py TSLA --work-dir work/TSLA_20251220
```

**Arguments:**
- `symbol`: Stock ticker symbol
- `--work-dir`: Work directory path (required)

**Output (05_wikipedia/):**
- `wikipedia_summary.txt` - Wikipedia page summary with page title and URL
- `wikipedia_metadata.json` - Page metadata (title, URL, lengths)

**Ticker Mapping:**
Built-in mapping for common tickers (TSLA, AAPL, MSFT, GOOGL, etc.)
Falls back to heuristic search patterns if ticker not in mapping

**Features:**
- User-agent compliant with Wikipedia API guidelines
- Multiple search strategies for finding correct page
- Extracts clean summary text

#### 8. research_analysis.py

**Deep analysis research phase** - generates analytical insights using Perplexity AI.

**Purpose:**
- Deep dive analysis on business model, competitive landscape, and risks
- Generate investment thesis with bull/bear cases
- SWOT analysis and risk assessment

**Usage:**
```bash
./skills/research_analysis.py TSLA --work-dir work/TSLA_20251220
```

**Arguments:**
- `symbol`: Stock ticker symbol
- `--work-dir`: Work directory path (required)

**Output (06_analysis/):**
- `business_model_analysis.md` - 5-section deep dive on business model
- `competitive_analysis.md` - Competitive landscape and dynamics
- `risk_analysis.md` - Recent news, analyst reports, legal/regulatory issues
- `investment_thesis.md` - SWOT, bull/bear cases, critical watch points

**Business Model Analysis Sections:**
1. Core Business & Products/Services
2. Revenue Streams (breakdown, recurring vs one-time, geographic)
3. Customer Segments & Monetization (CAC, churn, LTV)
4. Market Characteristics (cycle, seasonality, size, margins)
5. Competitive Advantages (network effects, switching costs, brand, IP)

**Competitive Analysis Sections:**
1. Main Competitors (direct, adjacent, emerging)
2. Competitive Comparison (market share, differentiation, pricing, growth)
3. Competitive Dynamics (recent changes, winners/losers, threats/opportunities)

**Risk Analysis Coverage:**
1. Analyst Reports & Rating Changes (with firm names and dates)
2. Investigative Reports (critical journalism, short-seller reports)
3. Executive & Governance (management changes, insider trading, compensation)
4. Operational Developments (launches, restructuring, M&A, supply chain)
5. Legal & Regulatory (lawsuits, investigations, compliance)
6. Financial Performance (earnings, guidance, unexpected developments)

**Investment Thesis Sections:**
1. SWOT Analysis (Strengths, Weaknesses, Opportunities, Threats)
2. Bull Case (best-case assumptions, catalysts, upside potential)
3. Bear Case (worst-case assumptions, risks, downside potential)
4. Base Case & Risk/Reward (most likely scenario, risk level)
5. Critical Watch Points (metrics to monitor, upcoming catalysts, warning signs)

**Environment:**
- Requires `PERPLEXITY_API_KEY` environment variable

**Features:**
- Uses sonar-pro model for high-quality analysis
- 5000-8000 token responses for comprehensive coverage
- Retry logic with exponential backoff

#### 9. research_report.py

**Report generation phase** - assembles comprehensive analyst-style research report.

**Purpose:**
- Synthesize all research data into cohesive report
- Generate markdown and optionally HTML format
- Create professional equity research document

**Usage:**
```bash
# Generate markdown report
./skills/research_report.py TSLA --work-dir work/TSLA_20251220

# Generate HTML report
./skills/research_report.py TSLA --work-dir work/TSLA_20251220 --format html

# Use custom template
./skills/research_report.py TSLA --work-dir work/TSLA_20251220 --template custom_template.md.j2
```

**Arguments:**
- `symbol`: Stock ticker symbol
- `--work-dir`: Work directory path (required)
- `--format`: Output format (default: markdown, options: markdown, html)
- `--template`: Template file to use (default: equity_research_report.md.j2)

**Output:**
- `research_report.md` - Comprehensive markdown research report
- `research_report.html` - HTML version (if --format html)

**Report Structure:**
The report synthesizes data from all phases into a professional equity research format with sections on:
- Executive summary and investment thesis
- Company overview and business description
- Financial analysis and key metrics
- Technical analysis and price trends
- Competitive landscape
- Recent news and developments
- Risk factors
- Analyst recommendations
- Bull/bear investment cases
- SWOT analysis

**Features:**
- Uses Jinja2 templating engine for flexible report formatting
- Loads and integrates data from all research phases
- Formats financial data with proper number formatting
- Includes chart images and references to detailed data files
- Clean, readable markdown output suitable for viewing or converting

**Template Location:**
- Templates stored in `templates/` directory in project root
- Default: `templates/equity_research_report.md.j2`

#### 10. research_deep.py

**Deep research phase** - comprehensive analysis using Claude Agent SDK with MCP tools.

**Purpose:**
- Perform deep research using Claude Sonnet 4.5 with extended thinking
- Access to 6 MCP servers for real-time data gathering and verification
- Generate comprehensive 9-section analyst-style report
- Fill gaps and verify information from initial research phases

**Usage:**
```bash
# Auto-infer work directory from symbol and date
./skills/research_deep.py TSLA

# Specify custom work directory
./skills/research_deep.py TSLA --work-dir work/TSLA_20251220

# Disable MCP tools (basic mode)
./skills/research_deep.py TSLA --no-tools
```

**Arguments:**
- `symbol`: Stock ticker symbol
- `--work-dir`: Work directory path (default: work/SYMBOL_YYYYMMDD)
- `--no-tools`: Disable MCP tools and use basic Claude API only

**Output (08_deep_research/):**
- `deep_research_output.md` - 9-section comprehensive analysis (~10K-20K characters)
- `deep_research_thinking.md` - Extended thinking process from Claude
- `tool_usage.txt` - Log of MCP tools used during research (if tools enabled)

**Report Sections:**
1. Short Summary Overall Assessment
2. Extended Profile (history, core business, recent major news)
3. Business Model (revenue streams, customer segments, competitive advantages)
4. Competitive Landscape (main competitors, market share, differentiation)
5. Supply Chain Positioning (upstream/downstream dependencies)
6. Financial & Operating Leverage (debt, margins, cash flow, capital allocation)
7. Valuation (methodologies, multiples, analyst opinions, volatility, macro sensitivity)
8. Recent Developments & Risk Factors (news search, analyst reports, executive profiles, legal/regulatory issues)
9. Conclusion (SWOT, bull/bear cases, risk level, watch points)

**MCP Servers Used (Advanced Mode):**
When tools are enabled, Claude has access to 6 MCP servers:
- `stock-symbol-server` - 6 financial tools from server.py (trades, 10-K, charts, technical analysis, ratios, peers)
- `alphavantage` - Alpha Vantage financial data API
- `yfinance` - Yahoo Finance data access
- `brave-search` - Web search for news and analyst reports
- `perplexity-ask` - AI-powered search for investigative reports
- `wikipedia` - Company history and background

**Hybrid Research Mode:**
- Receives `research_report.md` as context (all previously gathered data)
- Can use MCP tools to fill gaps, verify facts, and find recent developments
- Combines synthesis with fresh research for comprehensive analysis

**Environment:**
- Requires `ANTHROPIC_API_KEY` environment variable
- Requires `claude-agent-sdk` Python package (for MCP tools mode)
- Falls back to basic mode if Agent SDK not available

**Features:**
- Extended thinking enabled (10K token budget) for deep reasoning
- Async execution with proper MCP server lifecycle management
- Graceful degradation: full tools → basic mode on failure
- Tool usage tracking and logging
- Execution time: 2-5 minutes with tools, 30-60 seconds basic mode
- Cost: ~$1-2 per run with tools, ~$0.50-1 basic mode

**Data Sources:**
- Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
- MCP servers for real-time data (when enabled)
- Research report context from all previous phases

#### 11. research_final.py

**Final report assembly phase** - combines all research outputs into polished final report.

**Purpose:**
- Assemble comprehensive final report from all research phases
- Combine executive summary, charts, technical analysis, peer comparison, and deep research
- Export to multiple formats (markdown, Word, HTML)
- Create publication-ready equity research document

**Usage:**
```bash
# Auto-infer work directory from symbol and date
./skills/research_final.py TSLA

# Specify custom work directory
./skills/research_final.py TSLA --work-dir work/TSLA_20251220
```

**Arguments:**
- `symbol`: Stock ticker symbol
- `--work-dir`: Work directory path (default: work/SYMBOL_YYYYMMDD)

**Output:**
- `final_report.md` - Final polished markdown report (always generated)
- `final_report.docx` - Word document (if pandoc or python-docx available)
- `final_report.html` - Standalone HTML report (if pandoc or markdown available)

**Report Structure:**
The final report combines and polishes all research outputs:

1. **Executive Summary** - Extracted from deep research analysis
2. **Stock Chart** - 4-year weekly chart with technical indicators
3. **Technical Analysis Summary** - Key indicators table and trend signals
4. **Peer Comparison** - Enhanced 8-column table with financial metrics
5. **Comprehensive Deep Research Analysis** - Full 9-section deep analysis
6. **Investment Conclusion** - Strategic position, SWOT, watch points

**Enhanced Peer Comparison Table:**
Shows target company + up to 8 peers with metrics:
- Symbol, Name, Price, Market Cap
- P/E Ratio (Trailing)
- Revenue (TTM in billions)
- Net Profit Margin
- Return on Equity

**Multi-Format Export:**
- **Markdown (.md):** Always generated, clean and readable
- **Word (.docx):** Via pandoc (preferred) or python-docx (fallback)
- **HTML (.html):** Via pandoc (preferred) or markdown library (fallback)
  - Standalone file with embedded CSS
  - Responsive table styling
  - Direct browser viewing

**Features:**
- Jinja2 templating for flexible formatting
- Automatic format detection and graceful fallbacks
- Proper table formatting (no blank lines in markdown tables)
- Number formatting for financial data
- Embedded chart images with relative paths
- Clean, professional output suitable for distribution

**Template Location:**
- Templates stored in `templates/` directory in project root
- Used template: `templates/final_report.md.j2`

**Dependencies:**
- **Required:** jinja2, pandas (for data loading)
- **Optional for .docx:** pandoc (system package) or python-docx (Python package)
- **Optional for .html:** pandoc (system package) or markdown (Python package)

**Conversion Methods:**
1. **Preferred (pandoc):** Full-featured conversion with TOC, styling
   - Install: `brew install pandoc`
2. **Fallback (Python libraries):** Basic conversion with limited formatting
   - Install: `pip install python-docx markdown`

#### 12. research_stock_v3.py (Experimental)

**Agent-based orchestrator** - experimental architecture using autonomous agents for section synthesis.

**Status:** In development - agent synthesis not yet implemented

**Purpose:**
- Stage 1: Parallel data gathering (reuses research_stock.py logic)
- Stage 2: Spawn autonomous agents to write report sections in parallel
- Stage 3: Template assembly into final report

**Planned Architecture:**
Each report section (executive summary, business model, competitive landscape, etc.) gets an autonomous agent that:
- Receives detailed prompt for what to write
- Has access to relevant data loading tools
- Can reason about best way to structure the section
- Writes high-quality, data-driven content

**Usage:**
```bash
# Run with agent synthesis (when implemented)
./skills/research_stock_v3.py TSLA

# Use critic agent for quality review
./skills/research_stock_v3.py TSLA --use-critic

# Skip synthesis, only gather data
./skills/research_stock_v3.py TSLA --skip-synthesis
```

**Note:** This is an experimental feature designed to work with Claude Code's Task tool for spawning autonomous agents. Currently serves as a proof-of-concept.

### Supporting Library

#### agent_tools.py

**Data loading library** for agent-based workflows (not a standalone skill).

**Purpose:**
- Provides simple, focused functions for loading research data
- Designed for use by autonomous agents in v3 architecture
- Clean interface for accessing work directory contents

**Functions Available:**
- `read_technical_analysis()` - Technical indicators and signals
- `read_fundamentals()` - Company overview and metrics
- `read_income_statement()`, `read_balance_sheet()`, `read_cash_flow()` - Financial statements
- `read_key_ratios()` - Financial ratios time series
- `read_analyst_recommendations()` - Analyst ratings
- `read_news_stories()`, `read_business_profile()`, `read_executive_profiles()` - Perplexity research
- `read_sec_item1()` - SEC 10-K business description
- `read_wikipedia_summary()` - Wikipedia summary
- `read_business_model_analysis()`, `read_competitive_analysis()`, etc. - Deep analysis
- `read_investment_thesis()` - SWOT and bull/bear cases
- `get_section_data()` - Helper to load all relevant data for a report section

**Usage:**
```python
from agent_tools import read_technical_analysis, read_fundamentals

tech_data = read_technical_analysis('work/TSLA_20251220')
fund_data = read_fundamentals('work/TSLA_20251220')
```

---

## Future Skills (Planned)

**Portfolio Management:**
- `analyze_allocation.py`: Compare actual vs target allocations
- `rebalance_suggest.py`: Generate trade recommendations
- `historical_analysis.py`: Track allocation changes over time using archived snapshots

**Securities Research:**
- Enhanced agent-based synthesis in research_stock_v3.py
- Options analysis skill
- Earnings call transcript analysis
- Social sentiment analysis

## Requirements

**Environment:**
- Python 3.11+ (conda environment: `mcpskills`)
- Environment variables (stored in `.env` file):
  - `PERPLEXITY_API_KEY` - Perplexity AI API key (required for qualitative research and analysis)
  - `SEC_FIRM` / `SEC_USER` - SEC EDGAR credentials (required)
  - `FINNHUB_API_KEY` - Finnhub API key (recommended for peer lookup and symbol validation)
  - `ANTHROPIC_API_KEY` - Anthropic API key (optional for deep research with Claude Sonnet 4.5)
  - `OPENBB_PAT` - OpenBB Personal Access Token (optional fallback for peer lookup)

**Python Packages:**

*Portfolio Management:*
- pandas >= 2.0
- plotly >= 5.0 (for visualizations)

*Securities Research (Data Gathering):*
- yfinance (stock data and fundamentals - primary data source)
- finnhub-python (peer detection and symbol validation - recommended)
- openbb (OpenBB Platform - optional fallback for peer lookup)
- pandas >= 2.0
- numpy
- plotly >= 5.0 (for chart generation)
- talib (TA-Lib for technical indicators)
- openai (for Perplexity API - OpenAI-compatible)
- sec-edgar-downloader (for SEC filings)
- beautifulsoup4 (for HTML parsing)
- wikipediaapi (for Wikipedia data)
- python-dotenv (for environment variable management)

*Securities Research (Report Generation):*
- jinja2 (for report templating)
- anthropic (for Claude API access)
- claude-agent-sdk (for MCP server integration in deep research)
- mcp (Model Context Protocol - dependency of claude-agent-sdk)
- python-docx (optional, for Word document generation)
- lxml (for XML/HTML parsing)
- markdown (optional, for HTML report generation)

**Installation:**
```bash
# Activate conda environment
conda activate mcpskills

# Install core data gathering dependencies
pip install pandas plotly yfinance finnhub-python numpy TA-Lib openai sec-edgar-downloader beautifulsoup4 wikipedia-api python-dotenv

# Optional: Install OpenBB for fallback peer lookup
pip install openbb

# Install report generation dependencies
pip install jinja2 anthropic claude-agent-sdk python-docx lxml markdown

# Install system package for document conversion (macOS)
brew install pandoc
```

**API Keys Setup:**
Create a `.env` file in the project root:
```bash
# SEC EDGAR (required)
SEC_USER=your_email@example.com
SEC_FIRM=YourCompanyName

# Perplexity AI (required for qualitative research and analysis)
PERPLEXITY_API_KEY=your_perplexity_key_here

# Finnhub (recommended for peer lookup and symbol validation - free tier)
FINNHUB_API_KEY=your_finnhub_key_here

# Anthropic Claude (optional for deep research)
ANTHROPIC_API_KEY=your_anthropic_key_here

# OpenBB Platform (optional fallback for peer lookup)
OPENBB_PAT=your_openbb_pat_here

# Anthropic API (for deep research with Claude Sonnet 4.5)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**MCP Server Configuration** (for deep research with tools):
The deep research phase can use MCP servers configured in `~/Library/Application Support/Claude/claude_desktop_config.json`. The following servers are supported:
- `stock-symbol-server` - Local server.py with 6 financial tools
- `alphavantage` - Alpha Vantage financial data
- `yfinance` - Yahoo Finance data
- `brave-search` - Web search
- `perplexity-ask` - AI-powered search
- `wikipedia` - Company information

See the Claude Code documentation for MCP server configuration details.

## Development

### Creating New Skills

To create a new skill:

1. **Create the Python file** in the `skills/` directory
2. **Use the standard structure:**
   ```python
   #!/opt/anaconda3/envs/mcpskills/bin/python3
   """
   Skill Name and Purpose

   Brief description of what this skill does.

   Usage:
       ./skills/skill_name.py [arguments]

   Output:
       - Description of output files created
   """

   import os
   import sys
   import argparse
   from datetime import datetime

   def main():
       """Main execution function."""
       parser = argparse.ArgumentParser(description='Skill description')
       parser.add_argument('required_arg', help='Description')
       parser.add_argument('--optional-arg', default='default', help='Description')
       args = parser.parse_args()

       print("=" * 60)
       print("Skill Name")
       print("=" * 60)

       # Execute skill logic
       try:
           # Do work here
           print("✓ Success message")
           return 0
       except Exception as e:
           print(f"❌ Error: {e}")
           return 1

   if __name__ == '__main__':
       sys.exit(main())
   ```

3. **Make executable:** `chmod +x skills/your_skill.py`
4. **Test the skill:** Run with various arguments to ensure it works
5. **Update this README** with comprehensive documentation

### Skill Design Principles

- **Self-contained:** Each skill should be independently executable
- **Clear interface:** Use argparse with helpful descriptions
- **Error handling:** Comprehensive try/except blocks with informative messages
- **Directory management:** Use `os.makedirs(dir, exist_ok=True)` for output directories
- **Return codes:** Return 0 for success, 1 for failure
- **Output consistency:** Use consistent formatting (=== dividers, ✓/❌ symbols)
- **Dated archives:** Use `datetime.now().strftime('%Y%m%d')` for archival outputs
- **Documentation:** Multi-line docstring with usage examples and output description

