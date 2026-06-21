# Deployment Guide

CapitalLens AI is designed to run locally, in Docker, or on a simple cloud stack. Demo mode requires no API keys and is the recommended judging configuration.

## Local Demo

```bash
pip install -r requirements.txt
python run_backend.py
streamlit run frontend/streamlit_app.py
```

## Docker Compose

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:8501`
- Backend: `http://localhost:8000`
- Health: `http://localhost:8000/health`

## Streamlit Community Cloud

Use this for the fastest public demo link:

1. Push the repo to GitHub.
2. Open Streamlit Community Cloud.
3. Select the repository.
4. Set main file path to `frontend/streamlit_app.py`.
5. Add optional secrets:

```toml
DEMO_MODE = "true"
OPENAI_API_KEY = ""
OPENAI_MODEL = "gpt-4.1-mini"
NEWS_API_KEY = ""
CAPITALLENS_RAG_INDEX_PATH = "data/rag_index.sqlite"
```

The Streamlit app imports the local `app/` package directly, so the frontend can run independently for judging.

## Render or Railway

Recommended setup:

- Deploy backend as a web service using `Dockerfile.backend`.
- Deploy frontend as a separate web service using `Dockerfile.frontend`.
- Configure persistent disk or managed storage for:
  - `CAPITALLENS_DB_PATH`
  - `CAPITALLENS_RAG_INDEX_PATH`

## Production Notes

Before a real production rollout:

- Replace SQLite with PostgreSQL for multi-user runs and watchlist state.
- Use a managed vector store or ChromaDB/OpenSearch behind the current RAG interface.
- Add authentication and per-user tenant isolation.
- Add request rate limiting and structured logs.
- Add observability with traces for agent step latency, retrieval quality, and tool failures.
- Add a scheduler for watchlist scans.

