from __future__ import annotations

from app.agents.filing_rag import FilingRAGAgent
from app.agents.news import NewsAgent
from app.agents.risk import RiskAgent
from app.config import Settings
from app.tools.finance_tools import fetch_market_data


def test_risk_scoring_detects_tesla_watch_items(tmp_path) -> None:
    settings = Settings(demo_mode=True, rag_index_path=tmp_path / "rag_index.db")
    market = fetch_market_data("TSLA", settings)
    news = NewsAgent(settings).run("TSLA")
    filing = FilingRAGAgent().run("TSLA")
    matrix = RiskAgent().run(market, news, filing)

    assert matrix.risk_score >= 45
    assert any(risk.category == "Valuation" for risk in matrix.risks)
    assert any(risk.severity >= 4 for risk in matrix.risks)
    assert matrix.summary


def test_lower_risk_company_scores_below_high_risk_threshold(tmp_path) -> None:
    settings = Settings(demo_mode=True, rag_index_path=tmp_path / "rag_index.db")
    market = fetch_market_data("MSFT", settings)
    news = NewsAgent(settings).run("MSFT")
    filing = FilingRAGAgent().run("MSFT")
    matrix = RiskAgent().run(market, news, filing)

    assert 0 <= matrix.risk_score <= 100
    assert matrix.risk_score < 75
