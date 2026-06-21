from __future__ import annotations

from app.main import CapitalLensOrchestrator
from app.schemas.models import ResearchRequest
from app.storage.database import add_watchlist_ticker, list_watchlist


def test_complete_demo_research_report_generation(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CAPITALLENS_DB_PATH", str(tmp_path / "watchlist.db"))
    monkeypatch.setenv("CAPITALLENS_RAG_INDEX_PATH", str(tmp_path / "rag_index.db"))
    result = CapitalLensOrchestrator().run_research(ResearchRequest(query="AAPL", mode="Quick Scan", demo_mode=True))

    markdown = result.report.markdown
    assert result.run_id
    assert result.bundle.market_data.ticker == "AAPL"
    assert "# CapitalLens AI Research Memo" in markdown
    assert "## 1. Executive Summary" in markdown
    assert "RAG Source Integrity" in markdown
    assert "## 10. Sources & Citations" in markdown
    assert "Disclaimer" in markdown
    assert "personalized trading recommendation" in markdown
    assert result.report.citations
    assert result.bundle.filing_rag.diagnostics is not None
    assert result.bundle.scores.confidence in {"Low", "Medium", "High"}


def test_watchlist_demo_fallback_uses_sqlite(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "watchlist.db"
    monkeypatch.setenv("CAPITALLENS_DB_PATH", str(db_path))

    item = add_watchlist_ticker("Tesla", db_path=db_path)
    assert item.ticker == "TSLA"
    assert [entry.ticker for entry in list_watchlist(db_path=db_path)] == ["TSLA"]


def test_durable_agent_events_are_persisted(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "agent_runs.db"
    monkeypatch.setenv("CAPITALLENS_DB_PATH", str(db_path))
    monkeypatch.setenv("CAPITALLENS_RAG_INDEX_PATH", str(tmp_path / "rag_index.db"))

    result = CapitalLensOrchestrator().run_research(ResearchRequest(query="MSFT", mode="Quick Scan", demo_mode=True))

    from app.storage.database import get_agent_events

    events = get_agent_events(result.run_id, db_path=db_path)
    assert len(events) >= 10
    assert events[0]["agent_name"] == "PlannerAgent"
    assert any(event["agent_name"] == "CriticAgent" and event["status"] == "complete" for event in events)
