# Equity Research and Portfolio Management Skills

A collection of Claude Code skills for portfolio analysis, categorization, and restructuring.

## Overview

This project uses a **skills-based architecture** where each skill is a standalone Python script that performs a specific portfolio management task. Skills can be run independently or orchestrated together for complex workflows.

## Quick Start

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
fidelity/
├── import/              # Fidelity CSV exports (Portfolio_Positions_*.csv)
├── data/                # Aggregated data and mappings
│   ├── aggregate_positions.csv       # Current aggregated positions
│   ├── aggregate_positions_YYYYMMDD.csv  # Dated archives
│   └── security_mapping.csv          # Symbol → Category mappings
├── dataviz/             # Interactive visualizations
│   └── allocation_sunburst_YYYYMMDD.html
├── skills/              # Portfolio management skills
│   ├── aggregate_positions.py
│   ├── visualize_allocation.py
│   └── README.md        # Detailed skill documentation
├── CLAUDE.md            # Instructions for Claude Code
└── README.md            # This file
```

## Available Skills

### 1. Position Aggregation
**File:** `skills/aggregate_positions.py`

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

### 2. Allocation Visualization
**File:** `skills/visualize_allocation.py`

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

## Planned Skills

Future skills for portfolio restructuring:

### 3. Allocation Analysis
**Purpose:** Compare actual vs target allocations, identify rebalancing needs

```bash
./skills/analyze_allocation.py
```

**Planned Features:**
- Load target allocation percentages by L1 category
- Calculate variance (actual - target)
- Generate rebalancing recommendations in dollars
- Export rebalancing report to CSV
- Create actual vs target comparison chart

### 4. Rebalancing Optimizer
**Purpose:** Generate optimal trade orders to reach target allocation

```bash
./skills/optimize_rebalance.py
```

**Planned Features:**
- Minimize number of trades
- Consider transaction costs
- Respect tax implications (tax-loss harvesting)
- Account-specific constraints (IRA vs taxable)
- Generate trade list with order details

### 5. Historical Trend Analysis
**Purpose:** Track allocation changes over time using archived snapshots

```bash
./skills/analyze_trends.py
```

**Planned Features:**
- Load historical aggregate_positions archives
- Calculate allocation drift over time
- Identify positions with significant value changes
- Generate time-series charts
- Export trend analysis to CSV

### 6. Risk Analysis
**Purpose:** Analyze portfolio risk metrics and concentration

```bash
./skills/analyze_risk.py
```

**Planned Features:**
- Calculate position concentration (% of portfolio)
- Identify over-concentrated positions
- Analyze category-level risk distribution
- Flag positions exceeding risk thresholds
- Generate risk report

### 7. Performance Tracking
**Purpose:** Calculate returns and compare to benchmarks

```bash
./skills/track_performance.py
```

**Planned Features:**
- Calculate time-weighted returns
- Compare to benchmark indices (S&P 500, AGG, etc.)
- Calculate Sharpe ratio and volatility
- Track performance by category
- Generate performance report with charts

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

### Creating New Skills

Skills should follow these conventions:

1. **Shebang:** `#!/opt/anaconda3/envs/fidelity/bin/python3`
2. **Executable:** `chmod +x skills/your_skill.py`
3. **Docstring:** Include usage instructions at top of file
4. **Arguments:** Use argparse for directory paths and options
5. **Error Handling:** Graceful failures with helpful messages
6. **Output:** Create directories as needed, use dated archives
7. **Documentation:** Update `skills/README.md` with skill details

### Python Environment

```bash
# Activate conda environment
conda activate fidelity

# Install required packages
pip install pandas plotly
```

**Dependencies:**
- Python 3.11+
- pandas >= 2.0
- plotly >= 5.0 (for visualization skills)

## Workflow

### Regular Portfolio Review

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
   - Open HTML file in browser
   - Drill down through categories
   - Identify areas needing rebalancing

6. **Analysis** (future skills)
   ```bash
   ./skills/analyze_allocation.py
   ./skills/optimize_rebalance.py
   ```

### Portfolio Restructuring

When rebalancing or restructuring the portfolio:

1. Run allocation analysis to identify needs
2. Use optimizer to generate trade recommendations
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

## License

This is a personal portfolio management tool. No license specified.

## Contributing

This is a personal project for managing a Fidelity portfolio. If you'd like to adapt these skills for your own portfolio, feel free to fork and modify.

## Support

For issues or questions about specific skills, see `skills/README.md` for detailed documentation of each skill's functionality and usage.
