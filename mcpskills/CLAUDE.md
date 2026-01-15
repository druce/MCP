# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project contains two distinct but related systems:

1. **Stock Research Skills** - Automated equity research report generation
2. **Portfolio Management Skills** - Fidelity portfolio analysis and rebalancing tools

Both use a **skills-based architecture** where each skill is a standalone executable Python script performing a specific task.

## Python Environment

This project requires Python 3.11 for OpenBB compatibility. Use conda:

```bash
# Activate environment
conda activate mcpskills

# Install dependencies
pip install -r requirements.txt

# TA-Lib requires system library (macOS)
brew install ta-lib
export TA_INCLUDE_PATH="$(brew --prefix ta-lib)/include"
export TA_LIBRARY_PATH="$(brew --prefix ta-lib)/lib"
pip install TA-Lib
```

## Required API Keys

Set these in `.env` file:

**Core (Required):**
- `PERPLEXITY_API_KEY` - Deep research analysis
- `SEC_FIRM` - SEC API firm identifier
- `SEC_USER` - SEC API user email

**Data Sources (Prioritized Fallback):**
- `FINNHUB_API_KEY` - **Recommended** - Free tier for peer lookup and symbol validation
  - Get free key at: https://finnhub.io/register
- `OPENBB_PAT` - Optional fallback for peer lookup (note: FMP peers may require paid subscription)
  - Only needed if Finnhub is not configured

**Optional:**
- `TIINGO_API_KEY` - Historical market data (currently unused, reserved for future use)
- `ANTHROPIC_API_KEY` - Claude API (for testing)
- `OPENAI_API_KEY` - OpenAI API (for testing)

**Data Source Priority:**
- Symbol validation/lookup: yfinance → Finnhub → OpenBB+FMP
- Peer lookup: Finnhub → OpenBB+FMP
- Fundamental data: yfinance (primary)

## Stock Research Skills System

### Quick Start

```bash
# Complete research for a stock (all phases)
./skills/research_stock.py TSLA --phases all

# Specific phases only
./skills/research_stock.py TSLA --phases technical,fundamental,report

# Regenerate report with different template
./skills/research_report.py TSLA --work-dir work/TSLA_20251222 --template analyst_report.md.j2
```

### Architecture

The research system uses a **7-phase pipeline** orchestrated by `research_stock.py`:

1. **Technical** (`research_technical.py`) - Charts, indicators, peer identification
2. **Fundamental** (`research_fundamental.py`) - Financial statements, ratios, news
3. **Research** (`research_perplexity.py`) - News, business profile, executives via Perplexity
4. **Analysis** (`research_analysis.py`) - Business model, competition, risks, investment thesis via Perplexity
5. **SEC** (`research_sec.py`) - 10-K Item 1 extraction
6. **Wikipedia** (`research_wikipedia.py`) - Company summary
7. **Report** (`research_report.py`) - Jinja2 template rendering

### Phase Dependencies

**CRITICAL DEPENDENCY:**
- **Phase 1 (Technical)** MUST run before Phase 2 (Fundamental)
  - Technical generates `01_technical/peers_list.json`
  - Fundamental needs this peer list to compare financial ratios
  - The orchestrator enforces this by running technical sequentially first
  - If running phases manually, always run technical before fundamental

**Other Dependencies:**
- **Phases 3-6** (Research, Analysis, SEC, Wikipedia) can run in any order or in parallel
- **Phase 7 (Report)** must run last - consumes all prior phase outputs

### Work Directory Structure

Each research run creates: `work/{SYMBOL}_{YYYYMMDD}/`

```
work/TSLA_20251222/
├── 00_metadata.json                # Phase tracking
├── 01_technical/
│   ├── chart.png                   # 4-year weekly chart
│   ├── technical_analysis.json     # All indicators
│   └── peers_list.json             # Competitor list
├── 02_fundamental/
│   ├── company_overview.json       # 40+ metrics
│   ├── income_statement.csv
│   ├── balance_sheet.csv
│   ├── cash_flow.csv
│   ├── key_ratios.csv
│   ├── analyst_recommendations.json
│   └── news.json
├── 03_research/                    # Initial Perplexity queries
│   ├── news_stories.md
│   ├── business_profile.md
│   └── executive_profiles.md
├── 04_sec/
│   ├── 10k_item1.txt
│   └── 10k_metadata.json
├── 05_wikipedia/
│   ├── wikipedia_summary.txt
│   └── wikipedia_metadata.json
├── 06_analysis/                    # Deep Perplexity analysis
│   ├── business_model_analysis.md
│   ├── competitive_analysis.md
│   ├── risk_analysis.md
│   └── investment_thesis.md
└── research_report.md              # Final output
```

### Report Templates

Templates live in `templates/` and use Jinja2 syntax:

- **`equity_research_report.md.j2`** (default) - 12-section professional format
- **`analyst_report.md.j2`** - Simpler 8-section format

Templates have access to all data from phases 1-6 via variables like `technical_analysis`, `peers`, `business_model_analysis`, etc.

### Key Technical Details

**Data Fetching (Multi-Provider Fallback):**
- **Symbol validation/lookup**: yfinance → Finnhub → OpenBB+FMP
  - `lookup_ticker.py` implements automatic fallback
- **Peer lookup**: Finnhub → OpenBB+FMP
  - `research_technical.py` implements automatic fallback
  - Finnhub uses GICS sub-industry classification
  - Peer data enriched with yfinance market info
- **Fundamental data**: yfinance (primary)
  - `research_fundamental.py` uses yfinance exclusively
- **Technical indicators**: TA-Lib (SMA, RSI, MACD, etc.)
- **Deep research**: Perplexity AI via API calls

**Phase Tracking:**
- `00_metadata.json` tracks completed phases
- Orchestrator skips completed phases on re-run
- Use `--skip-cleanup` flag to preserve old work directories

**Error Handling:**
- Individual phases fail gracefully
- Report generation works with partial data
- Phase failures logged but don't stop orchestrator

## Portfolio Management Skills System

### Quick Start

```bash
# 1. Export CSV files from Fidelity to import/
# 2. Aggregate positions
./skills/aggregate_positions.py

# 3. Generate visualization
./skills/visualize_allocation.py
```

### Architecture

Portfolio skills operate on Fidelity CSV exports:

1. **Aggregation** (`aggregate_positions.py`) - Consolidates 5 account types into single view
2. **Visualization** (`visualize_allocation.py`) - Interactive sunburst chart

### Category Hierarchy

Positions categorized by economic factors:

- **L1** - Economic factor: GROWTH, DEFLATION, INFLATION, CASH
- **L2** - Region/Asset class: US, INTERNATIONAL, TREASURY, TIPS
- **L3** - Sub-category: LARGECAP, SMALLCAP, INTERMEDIATE, LONGTERM
- **L4** - Specific strategy (optional)

Mappings defined in `data/security_mapping.csv`:

```csv
Symbol,L1,L2,L3,L4
OAKMX,GROWTH,US,LARGECAP,
VGIT,DEFLATION,TREASURY,INTERMEDIATE,
```

### Data Flow

```
import/Portfolio_Positions_*.csv
    ↓
skills/aggregate_positions.py
    ↓
data/aggregate_positions.csv
    ↓
skills/visualize_allocation.py
    ↓
dataviz/allocation_sunburst_YYYYMMDD.html
```

### Special Handling

**Cash Normalization:**
- `FDRXX**` → Cash
- `Pending Activity` → Cash

**Short Positions:**
- Negative quantity and value
- Correctly reduces category totals

**Multiple Accounts:**
- Same symbol summed across accounts
- Cost basis weighted by total cost / total quantity

## MCP Server (Legacy)

The `server.py` file implements an MCP server using FastMCP for Claude Desktop integration, but is separate from the skills-based architecture.

**MCP Tools:**
- `get_trades_for_symbol()` - Query blotter.db (fake trade data)
- `fetch_10k_item1()` - SEC filing extraction
- `make_stock_chart()` - Plotly chart generation
- `technical_analysis()` - TA-Lib indicators
- `get_fundamental_ratios()` - Financial metrics
- `get_peers()` / `get_peers_ratios()` - Peer analysis

**Running:**
```bash
# Development (from mcpskills directory)
LOGLEVEL=DEBUG mcp dev ./server.py

# Production
mcp run ./server.py

# Claude Desktop integration
mcp install ./server.py
```

Note: Use `./server.py` to explicitly run the server in the current directory (mcpskills), not the one in the parent MCP directory.

## Development Workflow

### Adding New Research Phase

1. Create `skills/research_newphase.py` with standalone execution
2. Add phase to orchestrator in `research_stock.py`
3. Update output directory (e.g., `07_newphase/`)
4. Modify report template to include new data
5. Update `EQUITY_RESEARCH_PROCESS.md` documentation

### Creating New Portfolio Skill

1. Follow conventions:
   - Shebang: `#!/opt/anaconda3/envs/mcpskills/bin/python3`
   - Use argparse for CLI arguments
   - Auto-create output directories
   - Generate dated archives (`filename_YYYYMMDD.ext`)

2. Common patterns:
   - Read from `data/aggregate_positions.csv`
   - Use `data/security_mapping.csv` for categories
   - Output to appropriate subdirectory (data/, dataviz/, analysis/)

### Testing Research Pipeline

```bash
# Test individual phases
./skills/research_technical.py TSLA --work-dir work/TSLA_test
./skills/research_fundamental.py TSLA --work-dir work/TSLA_test

# Test report generation with mock data
./skills/research_report.py TSLA --work-dir work/TSLA_test

# Full integration test
./skills/research_stock.py TSLA --phases all
```

## Common Issues

**"Invalid ticker symbol"**
```bash
./skills/lookup_ticker.py "Company Name"
```

**"No module named X"**
```bash
conda activate mcpskills
pip install -r requirements.txt
```

**"TA-Lib not found"**
```bash
brew install ta-lib
export TA_INCLUDE_PATH="$(brew --prefix ta-lib)/include"
export TA_LIBRARY_PATH="$(brew --prefix ta-lib)/lib"
pip install TA-Lib
```

**"Perplexity API key not found"**
```bash
echo 'PERPLEXITY_API_KEY=your_key_here' >> .env
```

**Phase fails but others succeed:**
- Check phase output for specific error
- Re-run failed phase individually
- Generate report with partial data (acceptable)

## File Locations

- **Skills:** `skills/*.py` - All executable scripts
- **Templates:** `templates/*.md.j2` - Jinja2 report templates
- **Work Output:** `work/{SYMBOL}_{YYYYMMDD}/` - Research outputs
- **Portfolio Data:** `data/` - Aggregated positions and mappings
- **Portfolio Viz:** `dataviz/` - Interactive HTML charts
- **Process Docs:** `EQUITY_RESEARCH_PROCESS.md` - Detailed research workflow
- **Roadmap:** `spec.md` - Portfolio skills development plan

## Important Notes

- All skills are executable: `chmod +x skills/*.py`
- Working directory auto-set to script location on startup
- Perplexity queries cost ~$0.36 per stock (36k tokens total)
- Skip `analysis` phase to reduce costs for quick research
- Older work directories deleted by default (use `--skip-cleanup` to preserve)
- Report generation works with partial data if phases fail
