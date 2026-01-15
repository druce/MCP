# Enhanced Multi-Agent Stock Research Architecture

### Phase 0: Initialization & Planning

These run first, all other tasks depend on them.

**User Interaction:**

Prompt: "Enter stock ticker to analyze:"
User: "AAPL"

@validator:

1. Confirm valid ticker using yfinance or stock-symbol-server
2. Get basic info: company name, sector, market cap
3. Display: "Analyzing Apple Inc. (AAPL) - Technology - $2.8T market cap"

Show standard outline (8 sections from your spec):

1. Short summary / overall assessment
2. Stock chart, technicals, comparison v. Peers, sankey of income statement
3. Company Profile
4.  Business Model  
5. Competitive Landscape
6. Supply Chain Positioning
7. Financial and Operating Leverage
8. Valuation
9. Recent Developments and Risk Factors
10. SWOT analysis, bull and bear case
11. Overall Assessment and critical watch points

Ask: "Any additional questions or custom sections?"

User can:

- Add custom sections: "Add section on R&D innovation"
- Modify existing: "Expand valuation to include scenario analysis"
- Skip sections: "Skip supply chain positioning"

Show updated outline, iterate until user confirms.



### Phase 1: Evergreen Tasks (Parallel Foundation Layer)

**Launch Orchestrator with Initial Task Queue:**



```
═══════════════════════════════════════════════════════
EVERGREEN TASKS (No dependencies - launch immediately)
═══════════════════════════════════════════════════════

@evergreen-1: Company Profile Baseline
├─ Tools: yfinance, web_search, web_fetch, wikipedia MCP
├─ Prompt: |
│   Gather baseline company information:
│   - Fetch 10-K Item 1 (Business Description)
│   - Yahoo Finance company profile
│   - Wikipedia overview
│   - Perplexity search for recent company summary
├─ Output: Raw text → Parse → Store
│   - Facts → Knowledge Graph (entities, relationships)
│   - Text chunks → Vector Store (embeddings)
│   - Structured data → SQLite (company_profile table)
├─ Budget: 100K tokens max
└─ Status: RUNNING → COMPLETE

@evergreen-2: Comparables Identification
├─ Tools: openbb, finviz, yfinance
├─ Prompt: |
│   Identify peer companies:
│   - Get industry peers from OpenBB
│   - Validate using Finviz screener (same sector, similar market cap)
│   - Confirm top 5-7 comparables
├─ Output:
│   - Store peer list → mem0 (persistent memory)
│   - Store peer metadata → SQLite (comparables table)
│   - Create relationships → Knowledge Graph (AAPL-[COMPETES_WITH]->MSFT)
├─ Budget: 50K tokens
└─ Status: RUNNING → COMPLETE

@evergreen-3: Fundamental Data Collection
├─ Dependencies: @evergreen-2 (needs comparable list)
├─ Tools: yfinance, finviz, openbb, stock-symbol-server
├─ Prompt: |
│   Collect financial data for target + comparables:
│   - Income statements (5 years)
│   - Balance sheets (5 years)
│   - Cash flows (5 years)
│   - Key ratios: P/E, PEG, P/B, ROE, ROIC, etc.
│   - Growth metrics: Revenue CAGR, EPS growth
├─ Output:
│   - Store all metrics → SQLite (fundamentals table)
│   - Create calculated ratios → Knowledge Graph
│   - Time series data → SQLite (for charts)
├─ Budget: 80K tokens
└─ Status: WAITING → RUNNING → COMPLETE

@evergreen-4: Technical Analysis
├─ Tools: stock-symbol-server (technical_analysis, make_stock_chart)
├─ Prompt: |
│   Analyze technical position:
│   - Generate price chart (1 year + 5 year)
│   - Calculate indicators: SMA(50, 200), RSI, MACD, Bollinger Bands
│   - Identify trend: uptrend/downtrend/sideways
│   - Support/resistance levels
│   - Volume analysis
├─ Output:
│   - Charts → Save to ./charts/
│   - Indicators table → SQLite
│   - Trend assessment → Knowledge Graph (AAPL-[HAS_TREND]->"Uptrend")
├─ Budget: 40K tokens
└─ Status: RUNNING → COMPLETE

@evergreen-5: Deep News Search
├─ Tools: web_search, web_fetch, yfinance (get_yahoo_finance_news)
├─ Prompt: |
│   Comprehensive news search (past 6 months):
│   - Recent earnings announcements
│   - Product launches/failures
│   - M&A activity, partnerships
│   - Regulatory issues, lawsuits
│   - Short-seller reports (Hindenburg, Citron, etc.)
│   - Executive changes
│   - Major customer wins/losses
│   
│   For EACH article found:
│   1. Extract key facts (per sentence)
│   2. Evaluate: Is this relevant? Non-trivial? Material?
│   3. If yes → Store in Knowledge Graph with metadata
│   4. Store full paragraph → Vector Store (for retrieval)
├─ Output:
│   - News items → SQLite (news table with sentiment, materiality)
│   - Facts → Knowledge Graph
│   - Text → Vector Store
├─ Budget: 150K tokens
└─ Status: RUNNING → COMPLETE

@evergreen-6: Sell-Side Research
├─ Tools: web_search, web_fetch
├─ Prompt: |
│   Find sell-side analyst research:
│   - Search for recent analyst reports (JPM, GS, MS, etc.)
│   - Morningstar analysis
│   - Seeking Alpha summaries
│   - Bloomberg/Reuters analyst consensus
│   
│   Extract from each:
│   - Price targets and ratings
│   - Key thesis points (bull/bear)
│   - Concerns or risks highlighted
│   - Valuation methodologies used
├─ Output:
│   - Analyst data → SQLite (analyst_coverage table)
│   - Consensus metrics → Knowledge Graph
│   - Report excerpts → Vector Store
├─ Budget: 100K tokens
└─ Status: RUNNING → COMPLETE

@evergreen-7: SEC Filings Deep Dive
├─ Tools: web_search (SEC EDGAR), web_fetch, custom SEC MCP if available
├─ Prompt: |
│   Analyze key SEC filings:
│   - Latest 10-K: Item 1 (Business), Item 1A (Risk Factors), Item 7 (MD&A)
│   - Latest 10-Q: Recent developments, updated risks
│   - Recent 8-Ks: Material events
│   - DEF 14A (Proxy): Executive comp, governance
│   
│   Extract and structure:
│   - Business segments → Knowledge Graph
│   - Risk factors → SQLite + Knowledge Graph
│   - MD&A insights → Vector Store
│   - Governance details → SQLite
├─ Output:
│   - Structured data → SQLite (filings table)
│   - Entities/relationships → Knowledge Graph  
│   - Long-form text → Vector Store
├─ Budget: 200K tokens (filings are long)
└─ Status: RUNNING → COMPLETE

@evergreen-8: Universal MCP Data Pull
├─ Tools: Jeff Emanuel's large universal MCP server (from your context)
├─ Prompt: |
│   Query comprehensive data sources:
│   - Market data feeds
│   - Alternative data sources
│   - Institutional ownership
│   - Options flow data
│   - Any other relevant data endpoints
├─ Output: Store all retrieved data appropriately
├─ Budget: 80K tokens
└─ Status: RUNNING → COMPLETE

@evergreen-9: Previous Tearsheet Review
├─ Tools: local file access
├─ Prompt: |
│   If we've analyzed this company before:
│   - Load previous tearsheet
│   - Extract still-relevant information
│   - Note what's changed since last analysis
│   - Identify areas needing fresh research
├─ Output:
│   - Previous insights → Vector Store (marked as "historical")
│   - Change deltas → Knowledge Graph
├─ Budget: 50K tokens
└─ Status: RUNNING → COMPLETE
```

### Knowledge Storage Architecture

python

```python
# SQLite Schema
"""
companies(
    ticker TEXT PRIMARY KEY,
    name TEXT,
    sector TEXT,
    industry TEXT,
    market_cap REAL,
    description TEXT
)

comparables(
    ticker TEXT,
    peer_ticker TEXT,
    similarity_score REAL,
    basis TEXT  -- 'industry', 'size', 'business_model'
)

fundamentals(
    ticker TEXT,
    metric_name TEXT,
    period DATE,
    value REAL,
    PRIMARY KEY(ticker, metric_name, period)
)

news(
    news_id INTEGER PRIMARY KEY,
    ticker TEXT,
    headline TEXT,
    content TEXT,
    source TEXT,
    pub_date DATE,
    sentiment REAL,  -- -1 to 1
    materiality INTEGER  -- 1-5 scale
)

analyst_coverage(
    ticker TEXT,
    firm TEXT,
    analyst TEXT,
    rating TEXT,  -- 'Buy', 'Hold', 'Sell'
    price_target REAL,
    date DATE
)

knowledge_facts(
    fact_id INTEGER PRIMARY KEY,
    subject TEXT,
    predicate TEXT,
    object TEXT,
    source TEXT,
    confidence REAL,
    timestamp DATE
)
"""

# Knowledge Graph (Neo4j-style or in-memory)
"""
Nodes: Company, Person, Product, Risk, Event
Relationships: COMPETES_WITH, SUPPLIES_TO, ACQUIRED, HAS_RISK, etc.

Example:
(AAPL:Company)-[COMPETES_WITH]->(MSFT:Company)
(AAPL:Company)-[HAS_PRODUCT]->(iPhone:Product)
(iPhone:Product)-[GENERATES_REVENUE {percentage: 52}]->(AAPL:Company)
(AAPL:Company)-[HAS_RISK {severity: 'high'}]->(China_Dependence:Risk)
"""

# Vector Store (ChromaDB)
"""
Collections:
- company_descriptions: Long-form company overviews
- news_articles: News content with metadata
- analyst_reports: Excerpts from research reports
- filings: SEC filing text chunks
- historical_analysis: Previous tearsheets

Each embedding includes metadata:
{
    'source': 'news' | 'filing' | 'analyst' | 'web',
    'date': '2025-01-14',
    'ticker': 'AAPL',
    'confidence': 0.9,
    'section_relevance': ['business_model', 'risks']
}
"""
```

### Phase 2: Section Agents (With Critic-Optimizer Loops)

Each section agent follows this pattern:

```markdown
@section-agent-{name}:
├─ Dependencies: ALL evergreen tasks must be COMPLETE
├─ Budget: 150K tokens, max 3 iterations
└─ Process Flow:

STEP 1: INITIAL RETRIEVAL
├─ Query SQLite for structured data relevant to section
├─ Query Knowledge Graph for relationships
├─ Query Vector Store (semantic search) for contextual info
└─ Assemble retrieval results

STEP 2: DRAFT INITIAL SECTION
├─ Use section-specific prompt template
├─ Incorporate retrieved data
├─ Write comprehensive first draft
└─ Save to ./drafts/{section_name}_v1.md

STEP 3: CRITIC EVALUATION
├─ Prompt: |
│   You are a sophisticated Wall Street research analyst reviewing this section.
│   Evaluate on:
│   - **Completeness**: Are key questions answered? What's missing?
│   - **Data Support**: Are claims backed by specific data?
│   - **Insight Depth**: Surface-level or deep analysis?
│   - **Clarity**: Is it clear and well-structured?
│   - **Accuracy**: Any potential errors or inconsistencies?
│   
│   Provide:
│   1. Quality score (0-100)
│   2. Specific gaps or weaknesses
│   3. Questions that remain unanswered
│   4. Suggested improvements
├─ Output: Critic evaluation saved to ./critique/{section_name}_critique.json
└─ Decision:
    ├─ If score ≥ 85 AND no major gaps → COMPLETE
    └─ Else → Continue to STEP 4

STEP 4: GAP ANALYSIS & SEARCH PLAN
├─ Based on critic evaluation, identify information gaps
├─ Generate search plan:
│   - What specific data is missing?
│   - Which tools/sources to query?
│   - What questions to answer?
├─ Example search plan:
│   {
│     "gaps": [
│       "Need gross margin trends for past 5 years",
│       "Missing CEO's strategic vision from recent interviews",
│       "Unclear on R&D spending as % of revenue"
│     ],
│     "search_steps": [
│       {"tool": "sqlite", "query": "SELECT ... FROM fundamentals WHERE metric='gross_margin'"},
│       {"tool": "web_search", "query": "Tim Cook interview strategy 2024"},
│       {"tool": "knowledge_graph", "query": "MATCH (c:Company)-[r:SPENDS_ON]->(rd:RnD)"}
│     ]
│   }
└─ Save to ./search_plans/{section_name}_search_plan.json

STEP 5: EXECUTE SEARCH PLAN
├─ For each search step in plan:
│   ├─ Execute tool/query
│   ├─ Extract relevant information
│   ├─ Store new findings (if novel):
│   │   ├─ SQLite (structured data)
│   │   ├─ Knowledge Graph (facts/relationships)
│   │   └─ Vector Store (text chunks)
│   └─ Accumulate results
└─ Return filled gaps

STEP 6: REWRITE SECTION
├─ Incorporate new information from search execution
├─ Address specific weaknesses from critic
├─ Improve clarity, depth, data support
├─ Save to ./drafts/{section_name}_v{N}.md
└─ Increment iteration counter

STEP 7: ITERATION CHECK
├─ If iterations < max_iterations (3):
│   └─ Return to STEP 3 (Critic Evaluation)
├─ Else if budget exceeded:
│   └─ Save best version, mark COMPLETE
└─ Else:
    └─ Mark COMPLETE

OUTPUT:
├─ Final section: ./sections/{section_name}.md
├─ Metadata: ./metadata/{section_name}_meta.json
│   {
│     "iterations": 2,
│     "final_score": 88,
│     "tokens_used": 142000,
│     "gaps_remaining": ["Long-term guidance unclear"],
│     "data_sources": ["10-K", "Yahoo Finance", "3 news articles", "2 analyst reports"]
│   }
└─ Status: COMPLETE
```

### Specific Section Agent Configurations

```markdown
═══════════════════════════════════════════════════════
SECTION 1: COMPANY PROFILE
═══════════════════════════════════════════════════════
@section-agent-company-profile:
├─ Dependencies: evergreen-1, evergreen-4, evergreen-7
├─ Initial Retrieval:
│   - SQLite: company basics, financial summary
│   - Knowledge Graph: founding history, key milestones, current structure
│   - Vector Store: "company history", "business overview"
├─ Draft Prompt: |
│   Write comprehensive company profile including:
│   
│   **History & Origin Story:**
│   - Founding story with key dates
│   - Pivotal moments that shaped the company
│   - Evolution of business model
│   
│   **Core Business & Competitors:**
│   - Primary products/services (revenue breakdown)
│   - Target markets and customers
│   - Direct competitors (name top 5 with brief comparison)
│   
│   **Recent Major Developments:**
│   - Last 12 months: M&A, product launches, strategic shifts
│   - Upcoming catalysts or events
│   
│   **Stock Chart:**
│   - Embed chart image from ./charts/
│   - Brief commentary on technical position
│   
│   **Technical Indicators Table:**
│   | Indicator | Value | Signal |
│   |-----------|-------|--------|
│   | 50-day SMA | $XXX | Above/Below price |
│   | 200-day SMA | $XXX | Golden/Death cross |
│   | RSI | XX | Overbought/Oversold/Neutral |
│   | MACD | X.XX | Bullish/Bearish |
│   
│   **Key Fundamental Ratios Table:**
│   | Metric | TICKER | Peer Avg | Industry |
│   |--------|--------|----------|----------|
│   | P/E | XX.X | XX.X | XX.X |
│   | P/B | X.X | X.X | X.X |
│   | ROE | XX% | XX% | XX% |
│   | Debt/Equity | X.X | X.X | X.X |
│   | Rev Growth (3yr) | XX% | XX% | XX% |
│   
│   **Income Statement Sankey Chart:**
│   - Create Sankey diagram showing revenue flow through income statement
│   - Revenue → COGS → Gross Profit → OpEx categories → Net Income
│   - Save visualization to ./charts/sankey_income.png
│   
│   Use specific data from knowledge stores. Cite sources.
│   Target: 1500-2000 words
├─ Critic Focus:
│   - Origin story compelling and factual?
│   - Competitor comparison fair and data-backed?
│   - Recent developments truly material?
│   - All tables complete with accurate data?
│   - Charts properly embedded and explained?
└─ Budget: 150K tokens, 3 iterations max

═══════════════════════════════════════════════════════
SECTION 2: COMPANY BUSINESS MODEL
═══════════════════════════════════════════════════════
@section-agent-business-model:
├─ Dependencies: evergreen-1, evergreen-3, evergreen-7
├─ Initial Retrieval:
│   - SQLite: revenue breakdown by segment, customer data
│   - Knowledge Graph: (Company)-[OFFERS]->(Products), (Products)-[GENERATES]->(Revenue)
│   - Vector Store: "business model", "revenue streams", "monetization"
├─ Draft Prompt: |
│   Analyze business model in three parts:
│   
│   **Core Businesses, Products & Services:**
│   - Enumerate all major business lines
│   - For each: description, target market, scale
│   - Revenue contribution (% of total)
│   
│   **Revenue & Monetization:**
│   - Primary revenue streams with specifics
│   - Customer segments (consumer/enterprise/government)
│   - Pricing models (subscription/transaction/licensing)
│   - Key partnerships or channels
│   - Unit economics if available
│   
│   **Competitive Advantages (Moats):**
│   Assess presence and strength of:
│   - Network effects (direct/indirect)
│   - Switching costs (contractual/technical/data)
│   - Regulatory moats (licenses, patents, trade secrets)
│   - Brand value (pricing power evidence)
│   - Proprietary technology (hard to replicate)
│   - Distribution advantages (exclusive channels, scale)
│   
│   For each moat: Rate strength (Weak/Moderate/Strong)
│   Provide evidence from filings, news, analyst reports
│   
│   Target: 1200-1500 words
├─ Critic Focus:
│   - Business model clearly explained?
│   - Revenue breakdown accurate and detailed?
│   - Moat analysis rigorous (evidence-based, not aspirational)?
│   - Customer segments well-defined?
└─ Budget: 150K tokens, 3 iterations

═══════════════════════════════════════════════════════
SECTION 3: COMPETITIVE LANDSCAPE
═══════════════════════════════════════════════════════
@section-agent-competitive-landscape:
├─ Dependencies: evergreen-2, evergreen-3, evergreen-6
├─ Initial Retrieval:
│   - SQLite: competitor metrics, market shares
│   - Knowledge Graph: (Company)-[COMPETES_WITH]->(Competitor) relationships
│   - Vector Store: "competitive positioning", "market share", competitor names
├─ Draft Prompt: |
│   **Main Competitors:**
│   Identify and analyze:
│   - Direct competitors (same products/markets)
│   - Adjacent competitors (partial overlap)
│   - Emerging competitors (disruptive threats)
│   
│   For top 5-7 competitors:
│   
│   **Competitive Metrics Comparison Table:**
│   | Metric | TICKER | Comp 1 | Comp 2 | Comp 3 | Comp 4 |
│   |--------|--------|--------|--------|--------|--------|
│   | Market Share | X% | X% | X% | X% | X% |
│   | Revenue Growth (3Y) | XX% | XX% | XX% | XX% | XX% |
│   | Gross Margin | XX% | XX% | XX% | XX% | XX% |
│   | R&D as % Revenue | XX% | XX% | XX% | XX% | XX% |
│   | P/E Ratio | XX | XX | XX | XX | XX |
│   | EV/Sales | X.X | X.X | X.X | X.X | X.X |
│   
│   **Competitive Analysis:**
│   - Product differentiation: What makes each unique?
│   - Pricing power: Who can raise prices? Evidence?
│   - Growth trajectories: Who's gaining/losing share?
│   - Innovation pace: R&D spend, patent activity
│   - Customer loyalty metrics if available
│   
│   **Strategic Positioning:**
│   - Where does target company excel vs competitors?
│   - Where is it vulnerable?
│   - Likely competitive moves (pricing, M&A, new products)
│   
│   Use analyst reports and recent news for qualitative insights.
│   Target: 1200-1500 words
├─ Critic Focus:
│   - Comprehensive competitor identification?
│   - Metrics table complete and accurate?
│   - Analysis goes beyond surface comparisons?
│   - Strategic implications clear?
└─ Budget: 150K tokens, 3 iterations

═══════════════════════════════════════════════════════
SECTION 4: SUPPLY CHAIN POSITIONING
═══════════════════════════════════════════════════════
@section-agent-supply-chain:
├─ Dependencies: evergreen-1, evergreen-5, evergreen-7
├─ Initial Retrieval:
│   - SQLite: supplier data, distribution partners
│   - Knowledge Graph: (Company)-[SOURCES_FROM]->(Supplier), (Company)-[DISTRIBUTES_VIA]->(Channel)
│   - Vector Store: "supply chain", "suppliers", "distribution"
├─ Draft Prompt: |
│   **Upstream (Supplier-Side):**
│   - Key suppliers (top 5-10 by importance)
│   - Raw materials or components sourced
│   - Geographic concentration (single-country risk?)
│   - Supplier bargaining power assessment
│   - Supplier dependencies or lock-ins
│   
│   **Downstream (Customer/Distribution-Side):**
│   - Distribution channels (direct, retail, online, partners)
│   - Key distribution partners
│   - Customer concentration (top customers as % of revenue)
│   - Customer bargaining power
│   
│   **Supply Chain Risks:**
│   - Single points of failure
│   - Geographic concentration risks
│   - Inventory management approach (JIT vs buffer stock)
│   - Recent supply chain disruptions (from news search)
│   
│   **Supply Chain Advantages:**
│   - Vertical integration benefits
│   - Exclusive supplier relationships
│   - Superior logistics/distribution
│   
│   Target: 1000-1200 words
├─ Critic Focus:
│   - Key dependencies identified?
│   - Risk assessment thorough?
│   - Upstream and downstream balanced coverage?
└─ Budget: 120K tokens, 3 iterations

═══════════════════════════════════════════════════════
SECTION 5: FINANCIAL AND OPERATING LEVERAGE
═══════════════════════════════════════════════════════
@section-agent-leverage:
├─ Dependencies: evergreen-3, evergreen-7
├─ Initial Retrieval:
│   - SQLite: balance sheet data, debt metrics, cost structure
│   - Knowledge Graph: financial relationships
│   - Vector Store: "leverage", "debt", "fixed costs", "operating leverage"
├─ Draft Prompt: |
│   **Financial Leverage:**
│   - Total debt levels (absolute and as % of equity, EBITDA)
│   - Debt maturity schedule (near-term obligations)
│   - Interest coverage ratio (EBIT / Interest Expense)
│   - Credit ratings (S&P, Moody's, Fitch)
│   - Cost of debt (weighted average interest rate)
│   - Debt covenants or restrictions
│   
│   **Financial Leverage Table:**
│   | Metric | Current | 3Y Avg | Peer Avg |
│   |--------|---------|--------|----------|
│   | Debt/Equity | X.X | X.X | X.X |
│   | Debt/EBITDA | X.X | X.X | X.X |
│   | Interest Coverage | X.X | X.X | X.X |
│   | Current Ratio | X.X | X.X | X.X |
│   
│   **Operating Leverage:**
│   - Fixed vs variable cost structure
│   - Operating leverage calculation (% change EBIT / % change Sales)
│   - Margin sensitivity: If revenue grows 10%, what happens to EBIT margin?
│   - Scalability: Can they grow revenue without proportional cost increases?
│   - Breakeven analysis if data available
│   
│   **Assessment:**
│   - Is financial leverage appropriate for business model?
│   - Refinancing risks or opportunities?
│   - Operating leverage as competitive advantage or vulnerability?
│   
│   Target: 1000-1200 words
├─ Critic Focus:
│   - Leverage metrics comprehensive and accurate?
│   - Operating leverage analysis quantitative, not hand-wavy?
│   - Peer comparison meaningful?
└─ Budget: 120K tokens, 3 iterations

═══════════════════════════════════════════════════════
SECTION 6: VALUATION
═══════════════════════════════════════════════════════
@section-agent-valuation:
├─ Dependencies: evergreen-3, evergreen-6
├─ Initial Retrieval:
│   - SQLite: historical/projected financials, comp multiples
│   - Knowledge Graph: valuation-related facts
│   - Vector Store: "valuation", "DCF", analyst price targets
├─ Draft Prompt: |
│   **Valuation Methodologies:**
│   
│   **1. Market-Based (Comparables):**
│   - Current trading multiples vs peers
│   - P/E, P/B, EV/EBITDA, EV/Sales, PEG
│   - Historical valuation ranges (5-year)
│   - Premium/discount to peers (justified or not?)
│   
│   **Comps Valuation Table:**
│   | Multiple | TICKER | Peer Median | Implied Value |
│   |----------|--------|-------------|---------------|
│   | P/E (NTM) | XX.X | XX.X | $XXX |
│   | EV/EBITDA | XX.X | XX.X | $XXX |
│   | P/Sales | X.X | X.X | $XXX |
│   | PEG | X.X | X.X | $XXX |
│   
│   **2. Income-Based (DCF):**
│   - Key assumptions to discuss:
│     * Revenue growth rates (near-term, long-term)
│     * Margin expansion or compression
│     * Reinvestment requirements (capex, working capital)
│     * Terminal growth rate
│     * Discount rate (WACC calculation)
│   - Sensitivity analysis: What if growth is ±2%? WACC ±1%?
│   - Range of intrinsic values under different scenarios
│   
│   **3. Asset-Based:**
│   - Book value per share
│   - Tangible book value
│   - Sum-of-the-parts if applicable (multiple business segments)
│   - Relevant for asset-heavy businesses
│   
│   **4. LBO Analysis (if relevant):**
│   - Could private equity acquire at current price?
│   - IRR at various exit multiples
│   - Debt capacity
│   
│   **Analyst Price Targets:**
│   - Consensus target (from sell-side)
│   - Range of targets (high/low)
│   - Typical methodologies analysts use
│   
│   **Valuation Assessment:**
│   - Which methodology most appropriate for this company? Why?
│   - Fair value estimate range
│   - Current valuation attractive/expensive/fair?
│   - Key sensitivities (what drives valuation most?)
│   
│   Target: 1500-1800 words
├─ Critic Focus:
│   - All major methodologies covered?
│   - Assumptions clearly stated and reasonable?
│   - Sensitivity analysis provided?
│   - Conclusion balanced (not overly bullish/bearish)?
└─ Budget: 180K tokens, 3 iterations

═══════════════════════════════════════════════════════
SECTION 7: NEWS SEARCH AND RISK FACTORS
═══════════════════════════════════════════════════════
@section-agent-news-risks:
├─ Dependencies: evergreen-5, evergreen-7
├─ Initial Retrieval:
│   - SQLite: news items (last 6-12 months), filtered by materiality
│   - Knowledge Graph: (Company)-[HAS_RISK]->(Risk) nodes
│   - Vector Store: "risk factors", "lawsuit", "investigation", "controversy"
├─ Draft Prompt: |
│   **Recent News Themes:**
│   Categorize and summarize news from past 6-12 months:
│   
│   **Positive Developments:**
│   - Product launches (reception, early metrics)
│   - Partnerships or strategic alliances
│   - Large customer wins
│   - Regulatory approvals
│   - Beat earnings expectations
│   - Innovation announcements
│   
│   **Negative Developments:**
│   - Short-seller reports or allegations (detail claims)
│   - Regulatory investigations or lawsuits
│   - Product failures or recalls
│   - Operational issues or guidance cuts
│   - Supply chain disruptions
│   - Management turnover (departures)
│   - Competitive threats or lost business
│   
│   **Risk Factors (from 10-K + News):**
│   
│   **Business Risks:**
│   - Customer concentration
│   - Technology obsolescence
│   - Competitive intensity
│   - Market saturation
│   
│   **Financial Risks:**
│   - Leverage levels
│   - FX exposure
│   - Interest rate sensitivity
│   - Commodity price exposure
│   
│   **Operational Risks:**
│   - Key person dependencies
│   - Cybersecurity threats
│   - IT system failures
│   - Supply chain vulnerabilities
│   
│   **Regulatory/Legal Risks:**
│   - Pending litigation
│   - Regulatory changes (potential impact)
│   - Tax disputes
│   - Compliance issues
│   
│   **Reputational/ESG Risks:**
│   - Controversies (labor, environment, ethics)
│   - Social media backlash
│   - Brand damage incidents
│   
│   **Governance Concerns:**
│   - Board independence/diversity
│   - Executive compensation alignment
│   - Related party transactions
│   - Accounting quality questions
│   
│   For each risk: Rate severity (Low/Medium/High)
│   Provide recent examples or evidence
│   
│   Target: 1500-1800 words
├─ Critic Focus:
│   - All material news covered?
│   - Short-seller claims addressed objectively?
│   - Risk assessment thorough and balanced?
│   - Sources credible and recent?
└─ Budget: 180K tokens, 3 iterations

═══════════════════════════════════════════════════════
SECTION 8: OVERALL ASSESSMENT
═══════════════════════════════════════════════════════
@section-agent-overall-assessment:
├─ Dependencies: ALL previous sections (1-7) complete
├─ Initial Retrieval:
│   - Read all completed sections
│   - SQLite: full dataset for synthesis
│   - Knowledge Graph: holistic company view
│   - Vector Store: query for "strategic", "outlook", "recommendation"
├─ Draft Prompt: |
│   Synthesize all prior analysis into overall assessment:
│   
│   **Strategic Position:**
│   - Where does company stand in its industry?
│   - Competitive position (leader/challenger/niche)
│   - Strategic direction (offense/defense/transition)
│   
│   **SWOT Analysis:**
│   
│   **Strengths:**
│   - Top 3-5 with specific evidence
│   - What do they do better than anyone?
│   
│   **Weaknesses:**
│   - Top 3-5 vulnerabilities
│   - Where are they exposed?
│   
│   **Opportunities:**
│   - Growth avenues (organic/inorganic)
│   - Market expansion possibilities
│   - Innovation potential
│   
│   **Threats:**
│   - Competitive threats
│   - Disruption risks
│   - Macro headwinds
│   
│   **Bull Case (Optimistic Scenario):**
│   - What would drive outperformance?
│   - Key assumptions that must hold
│   - Potential upside (% or price target)
│   - Probability assessment
│   
│   **Bear Case (Pessimistic Scenario):**
│   - What could go wrong?
│   - Key risk that materializes
│   - Potential downside (% or price target)
│   - Probability assessment
│   
│   **Base Case (Most Likely):**
│   - Expected trajectory
│   - Fair value estimate
│   - Return potential vs risk-free rate
│   
│   **Watch Points (Areas for Continued Monitoring):**
│   - Key metrics to track quarterly
│   - Upcoming events or catalysts
│   - Signposts that would change thesis
│   - Further diligence areas
│   
│   **Investment Recommendation:**
│   - Buy / Hold / Sell (with conviction level)
│   - Target price (12-month)
│   - Risk/reward assessment
│   - Portfolio fit (who should own this?)
│   
│   Target: 1500-2000 words
├─ Critic Focus:
│   - Does assessment synthesize all prior sections coherently?
│   - Bull/bear cases specific and realistic?
│   - Recommendation clear and justified?
│   - Watch points actionable?
└─ Budget: 180K tokens, 3 iterations
```

### Phase 3: Synthesis & Final Polish

```markdown
═══════════════════════════════════════════════════════
FINAL ASSEMBLY & POLISH
═══════════════════════════════════════════════════════
@synthesis-agent:
├─ Dependencies: ALL section agents complete
├─ Budget: 200K tokens
└─ Process:

STEP 1: COMPILE REPORT
├─ Load all 8 completed sections
├─ Assemble in order with proper formatting using jinja2
├─ Generate table of contents with page numbers
├─ Add title page with:
│   - Company name and ticker
│   - Report date
│   - "For Informational Purposes Only" disclaimer
├─ Add appendices:
│   - Source bibliography (all sources cited)
│   - Definitions/glossary
│   - Detailed financial tables
│   - Additional charts
└─ Save to ./reports/TICKER_research_report_DRAFT.md

STEP 2: FINAL CRITIC EVALUATION
├─ Prompt: |
│   Review the complete report as a senior portfolio manager would:
│   
│   **Content Critique:**
│   - Is narrative arc coherent start to finish?
│   - Do sections flow logically?
│   - Any contradictions between sections?
│   - Are key questions answered?
│   - Appropriate depth for each topic?
│   
│   **Style Critique:**
│   - Professional, analytical Wall Street tone maintained?
│   - Appropriate for institutional investor audience?
│   - Clear, concise prose?
│   - Jargon explained when necessary?
│   
│   **Technical Critique:**
│   - Data accuracy spot checks
│   - Calculations verified
│   - Citations complete
│   - Charts/tables properly labeled
│   
│   **Repetition Check:**
│   - Identify any redundant content between sections
│   - Flag for removal or consolidation
│   
│   **Gap Check:**
│   - Any obvious omissions?
│   - Topics that deserve more coverage?
│   - Questions left unanswered?
│   
│   Provide:
│   - Overall quality score (0-100)
│   - List of specific issues to fix
│   - Prioritized by severity (Critical/Important/Minor)
├─ Output: Final critique saved to ./critique/final_report_critique.json
└─ If score < 85: Proceed to STEP 3; Else: Proceed to STEP 4

STEP 3: FINAL REWRITE & POLISH
├─ Address all Critical and Important issues from critique
├─ Remove repetition:
│   - If same fact appears in multiple sections, keep most relevant, cross-reference others
│   - Consolidate overlapping analysis
├─ Improve narrative flow:
│   - Add transition sentences between sections
│   - Ensure consistent terminology
│   - Unify voice and tone
├─ Enhance clarity:
│   - Simplify complex sentences
│   - Define technical terms on first use
│   - Add subheadings for easier navigation
├─ Verify all data:
│   - Cross-check key numbers against sources
│   - Ensure calculations are correct
│   - Update any stale data
└─ Save polished version to ./reports/TICKER_research_report_FINAL.md

STEP 4: GENERATE OUTPUTS
├─ Create PDF version (if possible):
│   - Professional formatting
│   - Page numbers, headers, footers
│   - Embedded charts and tables
│   - Save to ./reports/TICKER_research_report_FINAL.pdf
├─ Create executive summary (2-page):
│   - Company snapshot
│   - Investment thesis
│   - Key metrics table
│   - Recommendation with price target
│   - Top risks
│   - Save to ./reports/TICKER_executive_summary.md
├─ Create data supplement (Excel or CSV):
│   - All financial data in structured format
│   - Comparable company tables
│   - Historical data for charts
│   - Save to ./reports/TICKER_data_supplement.xlsx
└─ Generate metadata file:
    {
      "ticker": "AAPL",
      "report_date": "2025-01-14",
      "total_pages": 24,
      "sections": 8,
      "total_tokens_used": 1847000,
      "total_time_minutes": 28,
      "quality_score": 91,
      "data_sources": 47,
      "recommendation": "Buy",
      "price_target": 245.00,
      "analysts": ["evergreen", "section", "synthesis"]
    }

FINAL OUTPUT:
Present to user:
- Link to final report (markdown and PDF)
- Executive summary
- Key findings summary
- Report metadata
- Invitation for feedback or follow-up questions
```

## Orchestrator Implementation

python

```python
# Pseudo-code for orchestrator

class TaskQueue:
    def __init__(self):
        self.tasks = {}  # task_id -> Task object
        self.dependency_graph = {}  # DAG representation
        
    def add_task(self, task):
        self.tasks[task.id] = task
        self.dependency_graph[task.id] = task.dependencies
        
    def get_ready_tasks(self):
        """Return all tasks with satisfied dependencies"""
        ready = []
        for task_id, task in self.tasks.items():
            if task.status == "not_ready":
                deps_satisfied = all(
                    self.tasks[dep].status == "complete" 
                    for dep in task.dependencies
                )
                if deps_satisfied:
                    task.status = "ready"
                    ready.append(task)
        return ready
    
    def mark_complete(self, task_id):
        self.tasks[task_id].status = "complete"
        # Check if this enables new tasks
        self.plan_new_tasks(task_id)
    
    def plan_new_tasks(self, completed_task_id):
        """
        After task completes, decide if new research needed
        Example: If news search finds major lawsuit, 
        spawn new task to deep-dive on legal risks
        """
        completed_task = self.tasks[completed_task_id]
        
        # Analyze output
        if completed_task.name == "evergreen-5":  # News search
            # Check if any bombshell news
            if self.detect_material_event(completed_task.output):
                # Spawn additional investigation task
                new_task = Task(
                    name="deep-dive-legal",
                    dependencies=["evergreen-5"],
                    prompt="Investigate recent lawsuit in detail...",
                    budget=100000
                )
                self.add_task(new_task)

async def orchestrator_main(ticker):
    queue = TaskQueue()
    
    # Phase 1: Add all evergreen tasks (no dependencies)
    for evergreen in EVERGREEN_TASKS:
        queue.add_task(evergreen)
    
    # Phase 2: Add section tasks (depend on evergreens)
    for section in SECTION_TASKS:
        section.dependencies = [e.id for e in EVERGREEN_TASKS]
        queue.add_task(section)
    
    # Phase 3: Add synthesis (depends on all sections)
    synthesis = SynthesisTask(
        dependencies=[s.id for s in SECTION_TASKS]
    )
    queue.add_task(synthesis)
    
    # Main execution loop
    while not queue.all_complete():
        ready_tasks = queue.get_ready_tasks()
        
        if not ready_tasks:
            # Wait for running tasks to complete
            await asyncio.sleep(1)
            continue
        
        # Launch all ready tasks in parallel
        running = []
        for task in ready_tasks:
            task.status = "running"
            running.append(execute_subagent(task))
        
        # Wait for next task to complete
        done, pending = await asyncio.wait(
            running, 
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for completed in done:
            task = completed.result()
            queue.mark_complete(task.id)
            print(f"✅ {task.name} complete")
    
    print("🎉 All tasks complete!")
    return queue.tasks["synthesis"].output
```