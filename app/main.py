"""CapitalLens AI backend application and custom multi-agent orchestrator."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Callable

from app.agents.critic import CriticAgent
from app.agents.filing_rag import FilingRAGAgent
from app.agents.market_data import MarketDataAgent
from app.agents.news import NewsAgent
from app.agents.planner import PlannerAgent
from app.agents.report import ReportAgent
from app.agents.risk import RiskAgent
from app.agents.valuation import ValuationAgent
from app.config import Settings, get_settings
from app.schemas.models import AgentStep, NewsSummary, ResearchBundle, ResearchRequest, ResearchResult, Scores, WatchlistAlert, WatchlistScanResult
from app.storage.database import get_latest_scan, init_db, list_watchlist, save_scan_result
from app.tools.finance_tools import calculate_price_change_pct, calculate_volatility

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

ProgressCallback = Callable[[AgentStep], None]


class CapitalLensOrchestrator:
    """Clean custom multi-agent orchestrator for research workflows."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.planner = PlannerAgent()
        self.market_agent = MarketDataAgent(self.settings)
        self.news_agent = NewsAgent(self.settings)
        self.rag_agent = FilingRAGAgent(self.settings)
        self.risk_agent = RiskAgent()
        self.valuation_agent = ValuationAgent()
        self.report_agent = ReportAgent(self.settings)
        self.critic_agent = CriticAgent()

    def run_research(self, request: ResearchRequest, progress_callback: ProgressCallback | None = None) -> ResearchResult:
        settings = self.settings
        if request.demo_mode is not None and request.demo_mode != self.settings.demo_mode:
            settings = replace(self.settings, demo_mode=request.demo_mode)
            self.__init__(settings=settings)

        steps: list[AgentStep] = []

        def emit(name: str, status: str, detail: str) -> None:
            step = AgentStep(name=name, status=status, detail=detail)  # type: ignore[arg-type]
            steps.append(step)
            if progress_callback:
                progress_callback(step)

        emit("PlannerAgent", "running", "Creating autonomous research plan.")
        plan = self.planner.run(request)
        emit("PlannerAgent", "complete", f"Created {len(plan.tasks)} task plan for {request.mode}.")

        emit("MarketDataAgent", "running", "Resolving ticker and collecting market data.")
        market = self.market_agent.run(request.query)
        emit("MarketDataAgent", "complete", f"Loaded {market.company_name} market snapshot from {market.source}.")

        emit("NewsAgent", "running", "Scanning recent business events.")
        news = self.news_agent.run(market.ticker)
        emit("NewsAgent", "complete", f"Classified {len(news.items)} recent developments as {news.overall_tone}.")

        emit("FilingRAGAgent", "running", "Retrieving cited evidence from filing corpus.")
        filing = self.rag_agent.run(market.ticker, request.mode)
        emit("FilingRAGAgent", "complete", f"Retrieved {len(filing.evidence)} evidence chunks for memo grounding.")

        emit("RiskAgent", "running", "Scoring financial, business, market, and event risks.")
        risks = self.risk_agent.run(market, news, filing)
        emit("RiskAgent", "complete", f"Built risk matrix with aggregate score {risks.risk_score}/100.")

        emit("ValuationAgent", "running", "Computing valuation multiples and peer context.")
        valuation = self.valuation_agent.run(market)
        emit("ValuationAgent", "complete", "Prepared valuation snapshot and peer comparison.")

        scores = compute_scores(market, news, risks.risk_score)
        bundle = ResearchBundle(
            request=request,
            plan=plan,
            market_data=market,
            news=news,
            filing_rag=filing,
            risks=risks,
            valuation=valuation,
            scores=scores,
        )

        emit("ReportAgent", "running", "Generating analyst-style memo with citations.")
        report = self.report_agent.run(bundle)
        emit("ReportAgent", "complete", "Draft memo generated.")

        emit("CriticAgent", "running", "Reviewing memo for unsupported claims and safety language.")
        report = self.critic_agent.run(report, bundle)
        emit("CriticAgent", "complete", "Final memo passed deterministic critic review.")

        return ResearchResult(bundle=bundle, report=report, steps=steps)

    def scan_watchlist(self, progress_callback: ProgressCallback | None = None) -> list[WatchlistScanResult]:
        init_db(self.settings.database_path)
        results: list[WatchlistScanResult] = []
        for item in list_watchlist(self.settings.database_path):
            if progress_callback:
                progress_callback(AgentStep(name="WatchlistMonitor", status="running", detail=f"Scanning {item.ticker}."))
            previous = get_latest_scan(item.ticker, self.settings.database_path)
            research = self.run_research(ResearchRequest(query=item.ticker, mode="Quick Scan", demo_mode=self.settings.demo_mode))
            scan = build_watchlist_scan(research, previous)
            save_scan_result(scan, self.settings.database_path)
            results.append(scan)
        return results


def compute_scores(market, news: NewsSummary, risk_score: int) -> Scores:
    metrics = market.metrics
    financial = 45
    if metrics.operating_margin is not None:
        financial += 16 if metrics.operating_margin >= 0.25 else 9 if metrics.operating_margin >= 0.15 else -8
    if metrics.gross_margin is not None:
        financial += 8 if metrics.gross_margin >= 0.40 else 4 if metrics.gross_margin >= 0.25 else -3
    if metrics.revenue_growth is not None:
        financial += 12 if metrics.revenue_growth >= 0.10 else 7 if metrics.revenue_growth > 0 else -10
    if metrics.profit_growth is not None:
        financial += 12 if metrics.profit_growth >= 0.10 else 6 if metrics.profit_growth > 0 else -10
    if metrics.free_cash_flow_ttm is not None:
        financial += 8 if metrics.free_cash_flow_ttm > 0 else -8
    if metrics.current_ratio is not None:
        financial += 5 if metrics.current_ratio >= 1 else -5
    if metrics.debt_to_equity is not None:
        debt_ratio = metrics.debt_to_equity / 100 if metrics.debt_to_equity > 10 else metrics.debt_to_equity
        financial += 6 if debt_ratio <= 0.5 else -6 if debt_ratio > 1.2 else 0
    financial = _clamp(financial)

    momentum = 50
    price_change = calculate_price_change_pct(market.price_history)
    if price_change is not None:
        momentum += 15 if price_change > 5 else 7 if price_change > 0 else -12 if price_change < -5 else -4
    if len(market.price_history) >= 2 and market.price_history[0].close:
        total_return = (market.price_history[-1].close - market.price_history[0].close) / market.price_history[0].close * 100
        momentum += 12 if total_return > 15 else 6 if total_return > 0 else -10
    positives = sum(1 for item in news.items if item.impact == "positive")
    negatives = sum(1 for item in news.items if item.impact == "negative")
    momentum += positives * 4 - negatives * 6
    volatility = calculate_volatility(market.price_history)
    if volatility is not None and volatility > 40:
        momentum -= 8
    momentum = _clamp(momentum)

    if market.data_quality == "High" and len(news.items) >= 2 and market.citations:
        confidence = "High"
    elif market.data_quality == "Low":
        confidence = "Low"
    else:
        confidence = "Medium"

    return Scores(financial_health=financial, risk=_clamp(risk_score), momentum=momentum, confidence=confidence)


def build_watchlist_scan(research: ResearchResult, previous: WatchlistScanResult | None = None) -> WatchlistScanResult:
    market = research.bundle.market_data
    price_change = calculate_price_change_pct(market.price_history)
    risk_score = research.bundle.risks.risk_score
    momentum_score = research.bundle.scores.momentum
    alerts: list[WatchlistAlert] = []

    if price_change is not None and abs(price_change) >= 5:
        severity = "high" if abs(price_change) >= 10 else "medium"
        direction = "up" if price_change > 0 else "down"
        alerts.append(WatchlistAlert(ticker=market.ticker, severity=severity, category="Price Movement", message=f"{market.ticker} moved {direction} {abs(price_change):.1f}% versus the prior sample."))

    volatility = calculate_volatility(market.price_history)
    if volatility is not None and volatility >= 35:
        alerts.append(WatchlistAlert(ticker=market.ticker, severity="medium", category="Volatility", message=f"Estimated annualized volatility is elevated at {volatility:.1f}%."))

    negative_news = [item for item in research.bundle.news.items if item.impact == "negative"]
    if negative_news:
        alerts.append(WatchlistAlert(ticker=market.ticker, severity="medium", category="Negative News", message=f"{len(negative_news)} negative news item(s), including: {negative_news[0].title}"))

    if risk_score >= 70:
        alerts.append(WatchlistAlert(ticker=market.ticker, severity="high", category="Risk Score", message=f"Risk score is high at {risk_score}/100."))
    elif risk_score >= 55:
        alerts.append(WatchlistAlert(ticker=market.ticker, severity="medium", category="Risk Score", message=f"Risk score is elevated at {risk_score}/100."))

    metrics = market.metrics
    if (metrics.profit_growth is not None and metrics.profit_growth < 0) and (metrics.revenue_growth is None or metrics.revenue_growth <= 0.03):
        alerts.append(WatchlistAlert(ticker=market.ticker, severity="medium", category="Financial Trend", message="Profit growth is negative while revenue growth is limited."))

    if previous and previous.risk_score is not None and risk_score - previous.risk_score >= 10:
        alerts.append(WatchlistAlert(ticker=market.ticker, severity="high", category="Risk Score Increase", message=f"Risk score increased by {risk_score - previous.risk_score} points since the last scan."))

    return WatchlistScanResult(
        ticker=market.ticker,
        price_change_pct=price_change,
        risk_score=risk_score,
        momentum_score=momentum_score,
        alerts=alerts,
        snapshot={
            "company_name": market.company_name,
            "price": market.metrics.price,
            "currency": market.metrics.currency,
            "financial_health": research.bundle.scores.financial_health,
            "confidence": research.bundle.scores.confidence,
        },
    )


def _clamp(value: int | float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))


def run_research(query: str, mode: str = "Full Analyst Memo", demo_mode: bool | None = None) -> ResearchResult:
    orchestrator = CapitalLensOrchestrator()
    return orchestrator.run_research(ResearchRequest(query=query, mode=mode, demo_mode=demo_mode))  # type: ignore[arg-type]


def create_app():
    from fastapi import FastAPI

    from app.api.routes import router

    app = FastAPI(title="CapitalLens AI", version="1.0.0")
    app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, str | bool]:
        settings = get_settings()
        return {"status": "ok", "demo_mode": settings.demo_mode, "app": settings.app_name}

    return app
