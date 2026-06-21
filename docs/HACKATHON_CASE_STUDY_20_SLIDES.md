# CapitalLens AI - 20 Slide Hackathon Case Study Outline

## 1. Title
CapitalLens AI: Autonomous Financial Research and Productivity Agent

## 2. Problem
Public-company research is slow, fragmented, and hard to cite reliably.

## 3. Target Users
Analysts, students, founders, finance teams, and early-stage investment researchers.

## 4. Finance Track Fit
Company research, risk analysis, valuation snapshots, filings, market data, and watchlist monitoring.

## 5. Product Demo Snapshot
Show the working Streamlit UI, score cards, and generated memo.

## 6. Core Workflow
Ticker input -> autonomous plan -> tools -> RAG evidence -> scoring -> memo -> export.

## 7. Agentic AI Architecture
Planner, market data, news, filing RAG, risk, valuation, report, and critic agents.

## 8. Durable Agent Execution
Run IDs, persisted events, retries, status transitions, and observable agent logs.

## 9. Structured Outputs
Pydantic schemas for market data, news, RAG evidence, risks, valuation, scores, and final reports.

## 10. Advanced RAG Pipeline
Persistent SQLite chunk index, deterministic local embeddings, lexical scoring, vector similarity, and reranking.

## 11. Source Fidelity
Citation coverage, unsupported-topic detection, retrieval diagnostics, and critic validation.

## 12. Data Sources
yfinance optional live data, SEC/EDGAR best-effort filings, demo filings, demo company financials, and optional news provider.

## 13. Risk and Valuation Intelligence
Risk matrix, severity scores, valuation multiples, peer comparison, and analyst-style interpretation.

## 14. Watchlist Automation
SQLite watchlist with alerts for price moves, negative news, volatility, weak trends, and risk changes.

## 15. User Experience
Sidebar controls, progress timeline, tabs, charts, score cards, final memo viewer, and downloads.

## 16. Safety and Compliance
Educational disclaimer, no direct buy/sell instructions, citation-grounded claims, and missing-data handling.

## 17. Production Readiness
FastAPI backend, Streamlit frontend, Dockerfiles, Docker Compose, CI tests, `.env.example`, modular code, typed schemas.

## 18. Demo Reliability
Runs without API keys in deterministic demo mode with Apple, Microsoft, Tesla, Reliance, and TCS.

## 19. Business Impact
Reduces first-pass company research time and creates an auditable research memo workflow.

## 20. Roadmap
PostgreSQL, managed vector DB, embeddings provider, deeper SEC/XBRL ingestion, auth, scheduling, observability, and team workspaces.

