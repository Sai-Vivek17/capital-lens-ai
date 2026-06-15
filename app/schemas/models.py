"""Structured models for multi-agent research outputs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ResearchMode = Literal["Quick Scan", "Full Analyst Memo", "Risk-First Review"]
Impact = Literal["positive", "negative", "neutral"]
Confidence = Literal["Low", "Medium", "High"]


def utc_now() -> datetime:
    return datetime.now(UTC)


class Citation(BaseModel):
    id: str
    source: str
    title: str
    url: str | None = None
    date: str | None = None
    snippet: str


class AgentStep(BaseModel):
    name: str
    status: Literal["pending", "running", "complete", "warning", "error"] = "pending"
    detail: str = ""
    timestamp: datetime = Field(default_factory=utc_now)


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1, description="Ticker or company name")
    mode: ResearchMode = "Full Analyst Memo"
    demo_mode: bool | None = None


class PlanTask(BaseModel):
    agent: str
    objective: str
    tools: list[str] = Field(default_factory=list)
    expected_output: str


class ResearchPlan(BaseModel):
    query: str
    mode: ResearchMode
    tasks: list[PlanTask]
    success_criteria: list[str]


class PricePoint(BaseModel):
    date: str
    close: float


class FinancialTrendPoint(BaseModel):
    period: str
    revenue: float | None = None
    net_income: float | None = None


class FinancialMetrics(BaseModel):
    currency: str = "USD"
    price: float | None = None
    previous_close: float | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    revenue_ttm: float | None = None
    net_income_ttm: float | None = None
    free_cash_flow_ttm: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    revenue_growth: float | None = None
    profit_growth: float | None = None
    pe_ratio: float | None = None
    ps_ratio: float | None = None
    ev_ebitda: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    beta: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None


class MarketData(BaseModel):
    ticker: str
    company_name: str
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    description: str = ""
    metrics: FinancialMetrics
    price_history: list[PricePoint] = Field(default_factory=list)
    financial_trends: list[FinancialTrendPoint] = Field(default_factory=list)
    data_quality: Confidence = "Medium"
    source: str = "demo"
    citations: list[Citation] = Field(default_factory=list)


class NewsItem(BaseModel):
    title: str
    source: str
    date: str
    summary: str
    impact: Impact = "neutral"
    url: str | None = None
    citation_id: str | None = None


class NewsSummary(BaseModel):
    ticker: str
    items: list[NewsItem]
    overall_tone: Impact = "neutral"
    citations: list[Citation] = Field(default_factory=list)


class FilingEvidence(BaseModel):
    topic: str
    claim: str
    citation: Citation
    relevance_score: float = 0.0


class FilingRAGResult(BaseModel):
    ticker: str
    evidence: list[FilingEvidence]
    citations: list[Citation] = Field(default_factory=list)
    source_status: str = "demo filings"


class RiskItem(BaseModel):
    category: str
    description: str
    severity: int = Field(ge=1, le=5)
    evidence: str
    citation_id: str | None = None


class RiskMatrix(BaseModel):
    ticker: str
    risks: list[RiskItem]
    risk_score: int = Field(ge=0, le=100)
    summary: str


class ValuationMetric(BaseModel):
    name: str
    value: float | str | None
    interpretation: str


class PeerComparison(BaseModel):
    ticker: str
    company_name: str
    pe_ratio: float | None = None
    ps_ratio: float | None = None
    ev_ebitda: float | None = None


class ValuationSnapshot(BaseModel):
    ticker: str
    metrics: list[ValuationMetric]
    peers: list[PeerComparison] = Field(default_factory=list)
    summary: str


class Scores(BaseModel):
    financial_health: int = Field(ge=0, le=100)
    risk: int = Field(ge=0, le=100)
    momentum: int = Field(ge=0, le=100)
    confidence: Confidence


class ResearchBundle(BaseModel):
    request: ResearchRequest
    plan: ResearchPlan
    market_data: MarketData
    news: NewsSummary
    filing_rag: FilingRAGResult
    risks: RiskMatrix
    valuation: ValuationSnapshot
    scores: Scores
    generated_at: datetime = Field(default_factory=utc_now)


class ReportOutput(BaseModel):
    ticker: str
    company_name: str
    mode: ResearchMode
    markdown: str
    citations: list[Citation]
    critic_notes: list[str] = Field(default_factory=list)
    scores: Scores
    generated_at: datetime = Field(default_factory=utc_now)


class ResearchResult(BaseModel):
    bundle: ResearchBundle
    report: ReportOutput
    steps: list[AgentStep]


class WatchlistItem(BaseModel):
    ticker: str
    company_name: str | None = None
    created_at: str | None = None


class WatchlistAlert(BaseModel):
    ticker: str
    severity: Literal["low", "medium", "high"]
    category: str
    message: str
    created_at: datetime = Field(default_factory=utc_now)


class WatchlistScanResult(BaseModel):
    ticker: str
    scanned_at: datetime = Field(default_factory=utc_now)
    price_change_pct: float | None = None
    risk_score: int | None = None
    momentum_score: int | None = None
    alerts: list[WatchlistAlert] = Field(default_factory=list)
    snapshot: dict[str, Any] = Field(default_factory=dict)


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    """Return a dict for either Pydantic v1 or v2."""

    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
