"""FilingRAGAgent retrieves filing evidence for cited memo claims."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.schemas.models import FilingRAGResult
from app.tools.rag_tools import retrieve_filing_evidence, retrieve_filing_evidence_from_text
from app.tools.sec_tools import fetch_latest_10k_text


DEFAULT_TOPICS = [
    "business model revenue products services",
    "competition competitive advantage market",
    "regulatory legal compliance risk",
    "debt cash flow liquidity capital",
    "execution strategy management investment",
]


class FilingRAGAgent:
    name = "FilingRAGAgent"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def run(self, ticker: str, mode: str = "Full Analyst Memo") -> FilingRAGResult:
        topics = DEFAULT_TOPICS
        if mode == "Risk-First Review":
            topics = [
                "regulatory legal compliance risk",
                "debt liquidity cash flow financing",
                "competition margin pressure execution",
                "concentration supply chain customer dependence",
                "business model revenue products services",
            ]
        elif mode == "Quick Scan":
            topics = [
                "business model revenue products services",
                "competition regulatory risk",
                "cash flow debt liquidity",
            ]
        if not self.settings.demo_mode:
            filing = fetch_latest_10k_text(ticker, self.settings)
            if filing:
                evidence = retrieve_filing_evidence_from_text(
                    ticker=ticker,
                    company_name=ticker,
                    text=filing.text,
                    topics=topics,
                    source_url=filing.url,
                    source_title=f"{ticker} latest SEC {filing.form}",
                    source_date=filing.filing_date,
                    top_k_per_topic=1,
                )
                return FilingRAGResult(ticker=ticker, evidence=evidence, citations=[item.citation for item in evidence], source_status="SEC EDGAR")

        evidence = retrieve_filing_evidence(ticker, topics=topics, top_k_per_topic=1)
        return FilingRAGResult(ticker=ticker, evidence=evidence, citations=[item.citation for item in evidence])
