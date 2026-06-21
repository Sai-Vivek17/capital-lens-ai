# Submission Audit Checklist

## Current Strengths

- Finance track is clear and valuable.
- Multi-agent architecture is implemented with typed Pydantic outputs.
- Demo mode works without API keys.
- Hybrid RAG and citation diagnostics are implemented locally.
- CriticAgent checks safety language and source fidelity.
- Streamlit UI is demo-friendly.
- FastAPI backend exposes research and watchlist endpoints.
- Tests cover core agent, RAG, risk, and demo fallback paths.
- Dockerfiles, Docker Compose, CI, and deployment guide are included.

## Known Limitations

- There is no public live demo URL in the repository until the app is deployed.
- SQLite is suitable for demo/local persistence, not high-concurrency production.
- Local deterministic embeddings are reliable for offline judging but should be swapped for a domain embedding model in production.
- SEC ingestion is best-effort and should be expanded to robust 10-K/10-Q/XBRL pipelines.
- Authentication and tenant isolation are not implemented.

## Final Submission Requirements

- Add the public live demo URL to the README.
- Create the 20-slide PPT deck from `docs/HACKATHON_CASE_STUDY_20_SLIDES.md`.
- Run `pytest` before submission.
- Verify Streamlit demo mode from a clean browser session.
- Confirm no `.env`, local DB files, or secrets are committed.

