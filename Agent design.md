
# proof of concept deep research agent to analyze a stock.

Create a multi-agent AI to write a profile of a company from the perspective of an equity investor, in the matter-of-fact style of a Wall Street research analyst.


## Desired Report format, 8 sections:

Output will be a report structured in these sections

1. Company Profile

	- history with origin story and key historical milestones

	- core business and competitors

	- recent major developments

	- stock chart

	- table of technical indicators

	- table of key fundamental ratios

	- sankey chart  of income statement


2. Company Business Model:

	• Describe their core businesses, products and services.

	• Describe how they turn these business into money: their key revenue streams, customer segments, and monetization strategies.

	• Explain any sources of competitive advantage such as network effects, switching costs, regulatory moats, brands, difficult-to-replicate technology or distribution.


3. Competitive Landscape:

	• Identify their main competitors, including direct, adjacent, and emerging competitors.

	• Compare key metrics such as market share, product differentiation, pricing power, and growth trajectories.

4. Supply Chain Positioning:

	• Describe their role in the upstream (supplier-side) and downstream (customer/distribution) parts of the supply chain.

	• Identify key suppliers, partners, distributors, and any major dependencies or concentrations.

5. Financial and Operating Leverage:

	• Analyze the company’s use of financial leverage (debt levels, interest obligations, credit ratings).

	• Analyze operating leverage (fixed vs. variable cost structure, scalability, margin sensitivity to revenue changes).

6. Valuation:

	• Discuss appropriateness of various valuation methodologies, including income-based (e.g., DCF), asset-based (eg book value and sum of parts), market-based (e.g. comps), and LBO analysis

	• Highlight important valuation inputs and metrics (growth rates, margins, discount rates, terminal value assumptions).

7. News Search and Risk Factors:

	• Conduct a deep news search for significant positive and negative news items, including:

	• Short-seller reports or allegations.

	• Regulatory investigations or lawsuits.

	• Product failures, operational issues, or supply chain disruptions.

	• Major wins (e.g., partnerships, large customer wins, successful product launches).

	• Summarize key themes from recent media coverage, analyst reports, and public filings.

	• Note controversies, reputational risks, and governance concerns if any.

8. Overall Assessment:

	• Summarize the company’s strategic position, strengths, weaknesses, opportunities, threats, bull and bear cases, and any “watch points” for further diligence.

---

## multi-agent architecture

A coordinator-based multi-agent system where a main coordinator orchestrates specialized sub-agents. Use Python with asyncio for concurrent operations and Playwright for robust web scraping. Use SQLite, ChromaDB, and knowledge graph, for shared data across sub-agents.

Gather data; prompt ai to write individual sections using available tools to find information. Use a critic-optimizer to improve each section. Finally, combine the sections into a report and do a final critic-optimizer loop to polish it.

Flow:

1. Prompt the user: enter a stock to analyze

2. User enters a stock,

	- Confirm valid ticker, look up basic information using a tool

	- Show the standard deep research output outline above. Ask the user if any other specific questions. 

	- edit the outline, show the updated outline, repeat until OK

3. launch orchestrator. orchestrator manages tasks / sub-agents via a queue, (with dependencies so it represents a directed acyclic graph). loop:

	1. insert initial tasks into queue of tasks/sub-agents data structure. Tasks are structured as follows:

		- Task name

		- Optional initial prompt (maybe seed some stuff into the context)

		- Required main prompt, do x with the provided tools

		- Tools to use

		- Tools to query memory (SQLite, knowledge graph and vector store)

	    - Optional critic prompt - evaluate output from initial prompt according to 

		- Optional optimizer prompt , improve initial response based on critic eval

		- Optional test if complete

		- Agent budget , iterations or tokens

		- Task Dependencies, eligible to start when dependencies are satisfied

		- Atatus (not ready, ready, running, complete)

	2. Identify all tasks with no missing dependencies

	3. For each one that is ready to run, run sub- agent asynchronously

	4. Whenever a task returns

		1. Mark it complete
        
		2. Optionally plan based on current state, determine if it raises any new research avenues and tasks and put those in the queue

		3. Launch all tasks which are ready go as sub-agents

		4. Wait for next one to return

5. Evergreen tasks, always put into queue at start , all sections dependent on them

	1. Get company profile from: 10-k item 1, a couple of web sites like yahoo, perplexity, wikipedia

	2. Stuff that comes back, parse it, store facts in knowledge graph, text chunks in vector store

	3. get comparables from openbb. store list of comparables in mem0,

	4. get fundamentals from yahoo, finviz, - for target and comparables - store in mem0, put them in knowledge graph

	5. technicals, is uptrend or downtrend - store in knowledge graph

	6. do a deep news search

	7. search sell-side research like morningstar

	8. review tearsheet you made before and extract info, also review jeff emanuel's large universal mcp server


	9. most of these steps should be an mcp tool eg search for news, research, call extractor

		1. for each sentence, extract knowledge, ask if it looks relevant/nontrivial, put in knowledge graph

		2. put each paragraph in vector store

6. section_agent - writes a section, has an initial retrieval , prompt, critic and rewrite - put into queue with all evergreen tasks as dependencies, updating the prompt

		1. retrieve relevant info

		2. write initial section draft using the prompt

		3. reflection and gap analysis/critic eval.  you are a sophisticated analyst, what other question should you ask. if no gaps, or iterations / token buget exceeded, return

		4. based on crtic eval, generate a **search plan**, what are the gaps, additional stuff to look for? Decide to call multiple tools, local lookup, market data source, web search until you find the right answer

		5. run the search plan steps until you find all the right data

		6. rewrite the section

		7. loop until ok or section budget exceeded

7. synthesis, depends on all sections complete

8. rewrite and final polish: rewrite for narrative clarity, style, no duplication


## some web sites and scratch notes

https://www.anthropic.com/engineering/built-multi-agent-research-system

https://github.com/Marktechpost/AI-Notebooks/blob/main/GraphAIAgent_LangGraph_Gemini_Workflow_Marktechpost.ipynb

agents have dependencies
status , not started, running waiting subagents, complete etc.
current plan
budget
internal state and knowledge
global state and knowledge
tools including sub-agents

tools:
- web search - Serper or Brave API
- scraper - playwright
- profile
- triage: extract key facts and chunks, rate relevance, store or discard of no marginal relevance
- question answerer / info summarizer
- financial
- news search

overall -
- try mem0
- try basic openai adk
- build a basic mcp server
- record screen while doing deep research on mpt, extract the steps
- maybe try deepseek, others, get ideas
- write a deterministic python flow with the tools to write one report on eg medical properties trust

memory
letta: short term context window?

mem0: integrates vector store, knowledge graph,
https://arxiv.org/abs/2504.19413
https://mem0.ai/research

zep

cognee

crewai

memary -  https://github.com/kingjulio8238/Memary
langgraph flow
move to openai adk


use tiingo
https://sethhobson.com/2025/01/building-a-stock-analysis-server-with-mcp-part-1/

make a langchain agent
https://chatgpt.com/share/68458488-139c-8006-a129-a11920ee9211
mem0
https://chatgpt.com/share/684584c5-59e8-8006-b77c-e8664aef4195

agent-zero
https://chatgpt.com/share/683e500a-52d4-8006-b899-a71494ea3be3

anotia-wang
https://chatgpt.com/share/683e5113-4fd8-8006-97c7-926b704d3f0c

zhang
https://chatgpt.com/share/683e50fc-e45c-8006-9eb2-eb4d43ee4fd5

zilliz
https://chatgpt.com/share/683e50d3-2fc4-8006-bff1-99492610eebe

rigorous
https://chatgpt.com/share/683e5093-be60-8006-836a-b4b5b260257e
https://github.com/robertjakob/rigorous

https://github.com/assafelovic/gpt-researcher

https://github.com/SakanaAI/AI-Scientist
