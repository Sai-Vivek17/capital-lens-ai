# CapitalLens AI

Autonomous financial research and productivity agent for public-company analysis.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![RAG](https://img.shields.io/badge/RAG-Filing%20Evidence-111827?style=for-the-badge)
![SQLite](https://img.shields.io/badge/SQLite-Watchlist-003B57?style=for-the-badge&logo=sqlite&logoColor=white)

**Built by [Sai-Vivek17](https://github.com/Sai-Vivek17).**

CapitalLens AI is a polished AI agent product that converts a company name or stock ticker into a professional, cited research memo. It combines autonomous planning, market data tools, news/event analysis, filing evidence retrieval, risk scoring, valuation context, report generation, and a watchlist monitor in a local app that can be demoed without API keys.

> This project is for research and educational purposes only. It does not provide personalized investment, legal, tax, accounting, or trading advice.

## Product Screenshot

<img src="docs/images/capitallens-ai-demo.png" alt="CapitalLens AI working Streamlit app showing generated Apple research memo, score cards, and final memo tab" width="100%">

## Live Demo Status

- Streamlit Cloud target: [`https://capital-lens-ai.streamlit.app/`](https://capital-lens-ai.streamlit.app/)
- Status: deployment-ready, but public access still needs to be enabled from the Streamlit Cloud account before this should be submitted as the final live demo link.
- Local judging command: `streamlit run frontend/streamlit_app.py`

The target URL was checked on June 21, 2026 and redirected to Streamlit authentication, so the repository is ready for deployment but the app is not yet publicly accessible without account-side action.

## What It Does

CapitalLens AI helps analysts, students, founders, and finance teams research public companies quickly. A user enters a ticker such as `AAPL`, `MSFT`, `TSLA`, `RELIANCE.NS`, `TCS.NS`, or a company name like `Tesla`, chooses a research depth, and the agent produces a structured memo with cited sources.

The final output includes:

- Company overview
- Recent developments
- Financial health summary
- Key financial ratios
- Risk matrix
- Bull case and bear case
- Valuation snapshot
- Analyst-style conclusion
- Source citations
- Markdown and PDF export

## Core Features

- **Autonomous research planning:** PlannerAgent creates a task plan for each run.
- **Durable multi-agent architecture:** Dedicated agents for market data, news, filing RAG, risk, valuation, reporting, and critique, executed through a retry-aware run engine.
- **Advanced local RAG:** Persistent SQLite chunk index, deterministic local embeddings, BM25-style lexical scoring, vector similarity, reranking, and retrieval diagnostics.
- **RAG with citations:** FilingRAGAgent retrieves evidence from sample filings and best-effort SEC/EDGAR filings for supported US companies.
- **Source fidelity checks:** Citation coverage, unsupported-topic detection, retrieval scores, and critic notes are surfaced in the memo and UI.
- **Demo mode:** Works without API keys using deterministic sample data for Apple, Microsoft, Tesla, Reliance Industries, and TCS.
- **Live-data ready:** Optional adapters for yfinance, NewsAPI-style providers, SEC/EDGAR, and OpenAI-compatible LLM memo polish.
- **Structured outputs:** Pydantic models keep every agent output typed and predictable.
- **Scoring system:** Financial Health, Risk, Momentum, and Research Confidence scores.
- **Professional UI:** Streamlit dashboard with sidebar controls, progress timeline, tabs, charts, score cards, and downloads.
- **Watchlist monitor:** SQLite-backed watchlist that flags price moves, negative news, volatility, weak trends, and risk-score changes.
- **Export workflow:** Download generated reports as Markdown or PDF.
- **Test coverage:** Unit tests for ticker validation, demo fallback, metric extraction, hybrid RAG retrieval, durable event logging, risk scoring, and report generation.

## Phase 2 Production Hardening

This version includes a Phase 2 hardening layer focused on agent reliability and advanced RAG behavior:

- **Durable agent runs:** Every research run gets a `run_id`, persisted agent events, status transitions, and retry attempts.
- **Retry-safe execution:** Agent steps run through `DurableAgentExecutor`, with configurable retry count via `CAPITALLENS_AGENT_MAX_RETRIES`.
- **Persistent RAG index:** Filing chunks, metadata, token payloads, and deterministic embeddings are stored in `CAPITALLENS_RAG_INDEX_PATH`.
- **Hybrid retrieval:** Retrieval combines BM25-like lexical relevance, local vector similarity, and reranking overlap.
- **Retrieval diagnostics:** Each run reports indexed documents, indexed chunks, citation coverage, average top score, and evidence coverage.
- **Citation audit:** The critic checks missing citations, weak retrieval coverage, and unsupported retrieval topics before finalizing the memo.
- **Observable API:** Run events can be inspected through `GET /runs/{run_id}/events`.

## Agent Architecture

```mermaid
flowchart TD
    User["User enters ticker/company"] --> UI["Streamlit Research Console"]
    UI --> Orchestrator["CapitalLens Orchestrator"]
    API["FastAPI API"] --> Orchestrator

    Orchestrator --> Planner["PlannerAgent"]
    Orchestrator --> Durable["DurableAgentExecutor"]
    Planner --> Market["MarketDataAgent"]
    Planner --> News["NewsAgent"]
    Planner --> Filing["FilingRAGAgent"]
    Planner --> Risk["RiskAgent"]
    Planner --> Valuation["ValuationAgent"]
    Planner --> Report["ReportAgent"]
    Planner --> Critic["CriticAgent"]

    Market --> YFinance["yfinance"]
    Market --> DemoData["Demo financial data"]
    News --> NewsAPI["Optional news provider"]
    News --> DemoNews["Demo news events"]
    Durable --> Market
    Durable --> News
    Durable --> Filing
    Durable --> Risk
    Durable --> Valuation
    Durable --> Report
    Durable --> Critic

    Filing --> SEC["Best-effort SEC/EDGAR"]
    Filing --> Corpus["Sample filing corpus"]
    Filing --> RAGStore["Persistent SQLite RAG Index"]
    RAGStore --> Retriever["BM25 + local vectors + reranker"]

    Risk --> Matrix["Risk matrix"]
    Valuation --> Multiples["P/E, P/S, EV/EBITDA, peers"]
    Report --> Memo["Cited research memo"]
    Critic --> Audit["Citation and RAG fidelity audit"]
    Audit --> Final["Final reviewed memo"]
    Final --> Export["Markdown/PDF export"]

    Orchestrator --> Watchlist["SQLite watchlist monitor"]
    Durable --> Events["Run event log"]
```

## Tech Stack

| Layer | Tools |
| --- | --- |
| Frontend | Streamlit, pandas charts |
| Backend | FastAPI, Uvicorn |
| Data Models | Pydantic |
| Agents | Custom multi-agent orchestrator |
| Market Data | yfinance when available, deterministic demo fallback |
| Filing RAG | SEC/EDGAR best-effort adapter, sample filing corpus, persistent hybrid retrieval |
| Agent Reliability | Durable run IDs, persisted agent events, retries, checkpoints |
| News | Optional provider through environment variable, deterministic demo fallback |
| Storage | SQLite |
| Export | Markdown, PDF |
| Testing | pytest |

## Project Structure

```text
capital-lens-ai/
  app/
    main.py
    config.py
    agents/
      planner.py
      market_data.py
      news.py
      filing_rag.py
      risk.py
      valuation.py
      report.py
      critic.py
      durable.py
    tools/
      finance_tools.py
      news_tools.py
      rag_tools.py
      sec_tools.py
      export_tools.py
      advanced_rag.py
      citation_audit.py
    schemas/
      models.py
    storage/
      database.py
      rag_store.py
    api/
      routes.py
  frontend/
    streamlit_app.py
  data/
    demo_companies.json
    sample_filings/
  docs/
    images/
      capitallens-ai-demo.png
  tests/
  reports/
  README.md
  requirements.txt
  .env.example
  run_backend.py
  run_frontend.py
```

## Quick Start

```bash
git clone https://github.com/Sai-Vivek17/capital-lens-ai.git
cd capital-lens-ai
pip install -r requirements.txt
```

Run the backend:

```bash
python run_backend.py
```

Run the Streamlit app:

```bash
streamlit run frontend/streamlit_app.py
```

The app works immediately in demo mode, even without API keys.

## Submission Assets

- Deployment guide: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- Two-minute demo script: [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md)
- 20-slide case study outline: [`docs/HACKATHON_CASE_STUDY_20_SLIDES.md`](docs/HACKATHON_CASE_STUDY_20_SLIDES.md)
- Competition upload PDF: [`docs/case_study/CapitalLens_AI_The_Arch_Round1_Submission.pdf`](docs/case_study/CapitalLens_AI_The_Arch_Round1_Submission.pdf)
- Submission audit checklist: [`docs/SUBMISSION_AUDIT.md`](docs/SUBMISSION_AUDIT.md)
- Sample generated memo: [`docs/sample_reports/aapl_research_memo.md`](docs/sample_reports/aapl_research_memo.md)
- Docker Compose: [`docker-compose.yml`](docker-compose.yml)

## Environment Variables

Create a local `.env` file or set these variables in your shell:

```bash
DEMO_MODE=true
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
NEWS_API_KEY=
SEC_USER_AGENT=CapitalLensAI/1.0 contact@example.com
CAPITALLENS_DB_PATH=capital_lens_watchlist.db
CAPITALLENS_RAG_INDEX_PATH=data/rag_index.sqlite
CAPITALLENS_RAG_DIMS=384
CAPITALLENS_AGENT_MAX_RETRIES=2
```

`OPENAI_API_KEY` and `NEWS_API_KEY` are optional. When they are missing, CapitalLens AI uses deterministic demo responses and sample company data.

## Demo Flow

1. Open the Streamlit app.
2. Enter `AAPL`.
3. Select `Full Analyst Memo`.
4. Keep `Demo mode` enabled.
5. Click `Run Agent`.
6. Watch the progress timeline move through planner, market data, news, filing RAG, risk, valuation, report, and critic agents.
7. Review score cards, charts, risk matrix, valuation tab, and final memo.
8. Download the report as Markdown or PDF.
9. Open Watchlist Monitor.
10. Add `TSLA`, `MSFT`, or `RELIANCE.NS` and scan for alerts.

## API Usage

Start the backend:

```bash
python run_backend.py
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Generate a research report:

```bash
curl -X POST http://127.0.0.1:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query":"AAPL","mode":"Full Analyst Memo","demo_mode":true}'
```

Watchlist endpoints:

```bash
curl http://127.0.0.1:8000/watchlist
curl -X POST http://127.0.0.1:8000/watchlist/TSLA
curl -X POST http://127.0.0.1:8000/watchlist/scan
curl http://127.0.0.1:8000/watchlist/alerts
```

Inspect a durable agent run:

```bash
curl http://127.0.0.1:8000/runs/<run_id>/events
```

## Testing

```bash
pytest
```

Current verification:

```text
9 passed
```

The tests run in demo mode and do not require network access or API keys.

## Report Template

Generated memos follow a consistent analyst-style structure:

1. Executive Summary
2. Business Overview
3. Recent Developments
4. Financial Health
5. Valuation Snapshot
6. Key Risks
7. Bull Case
8. Bear Case
9. Agent Conclusion
10. Sources & Citations
11. Disclaimer

The conclusion avoids direct trading instructions and uses research-oriented language such as "requires caution", "appears resilient", or "needs further review".

## Example Demo Companies

| Ticker | Company |
| --- | --- |
| AAPL | Apple Inc. |
| MSFT | Microsoft Corporation |
| TSLA | Tesla, Inc. |
| RELIANCE.NS | Reliance Industries Limited |
| TCS.NS | Tata Consultancy Services Limited |

## Future Improvements

- Add optional ChromaDB/OpenSearch backends behind the current RAG interface.
- Expand SEC ingestion to full 10-K, 10-Q, exhibits, and XBRL pipelines.
- Add richer peer auto-discovery by sector, geography, and market cap.
- Add DCF and scenario-analysis modules.
- Add scheduled watchlist runs with email or Slack alerts.
- Add source freshness scoring by field.
- Add authentication and team workspaces.

## Resume Highlights

- Built an autonomous financial research agent using FastAPI, Streamlit, Pydantic, RAG, SQLite, and structured multi-agent orchestration.
- Implemented robust demo mode with deterministic financial data, news events, filing excerpts, risk analysis, and memo generation.
- Designed a watchlist monitor that detects unusual price movement, negative news, volatility, weak trends, and risk-score changes.
- Created a professional dashboard with progress timeline, score cards, charts, risk matrix, valuation tab, final memo viewer, and Markdown/PDF exports.

## AuthorS

**Vedakshari**  
GitHub: [github.com/vedakshari1-collab](https://github.com/vedakshari1-collab)
**Sai-Vivek17**  
GitHub: [github.com/Sai-Vivek17](https://github.com/Sai-Vivek17)

## Disclaimer

CapitalLens AI is for research and educational purposes only. It may contain errors, stale data, simplified assumptions, or incomplete source coverage. It does not provide personalized investment, legal, accounting, tax, or trading advice.
