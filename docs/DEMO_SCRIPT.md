# CapitalLens AI Demo Script

## Two-Minute Judge Demo

**0:00-0:15 - Problem**

Financial research is fragmented across filings, market data, news, and spreadsheets. Analysts need a fast first-pass memo that is cited, structured, and safe.

**0:15-0:35 - Product**

CapitalLens AI is an autonomous financial research agent. I enter a ticker such as `AAPL`, choose a research depth, and the system plans and executes the research workflow.

**0:35-1:05 - Agent Workflow**

Show the progress timeline:

- PlannerAgent creates the task plan.
- MarketDataAgent gathers financial metrics.
- NewsAgent classifies recent events.
- FilingRAGAgent retrieves cited filing evidence using hybrid RAG.
- RiskAgent builds a risk matrix.
- ValuationAgent compares valuation multiples.
- ReportAgent writes the memo.
- CriticAgent audits citations, safety language, and source fidelity.

**1:05-1:30 - Output**

Open the final memo tab. Point out:

- Financial Health, Risk, Momentum, and Confidence scores.
- RAG Source Integrity diagnostics.
- Bull case, bear case, risks, valuation, and citations.
- Markdown/PDF export.

**1:30-1:50 - Watchlist Automation**

Open Watchlist Monitor. Add `TSLA`, scan, and show alerts for price movement, negative news, volatility, and risk score.

**1:50-2:00 - Why It Wins**

CapitalLens AI is not a chatbot wrapper. It is a full-stack agentic RAG system with typed agent outputs, durable run logs, hybrid retrieval, citations, critic validation, and demo-safe fallbacks for live judging.

