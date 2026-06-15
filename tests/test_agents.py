from __future__ import annotations

from app.main import CapitalLensOrchestrator
from app.schemas.models import ResearchRequest
from app.storage.database import add_watchlist_ticker, list_watchlist


def test_complete_demo_research_report_generation(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CAPITALLENS_DB_PATH", str(tmp_path / "watchlist.db"))
    result = CapitalLensOrchestrator().run_research(ResearchRequest(query="AAPL", mode="Quick Scan", demo_mode=True))

    markdown = result.report.markdown
    assert result.bundle.market_data.ticker == "AAPL"
    assert "# CapitalLens AI Research Memo" in markdown
    assert "## 1. Executive Summary" in markdown
    assert "## 10. Sources & Citations" in markdown
    assert "Disclaimer" in markdown
    assert "personalized trading recommendation" in markdown
    assert result.report.citations
    assert result.bundle.scores.confidence in {"Low", "Medium", "High"}


def test_watchlist_demo_fallback_uses_sqlite(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "watchlist.db"
    monkeypatch.setenv("CAPITALLENS_DB_PATH", str(db_path))

    item = add_watchlist_ticker("Tesla", db_path=db_path)
    assert item.ticker == "TSLA"
    assert [entry.ticker for entry in list_watchlist(db_path=db_path)] == ["TSLA"]

