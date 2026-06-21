"""FilingRAGAgent retrieves filing evidence for cited memo claims."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.schemas.models import FilingRAGResult
from app.storage.rag_store import RAGIndexStore
from app.tools.advanced_rag import RAGDocument, RAGPipeline
from app.tools.finance_tools import get_demo_company
from app.tools.rag_tools import load_filing_text
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
        self.pipeline = RAGPipeline(
            store=RAGIndexStore(self.settings.rag_index_path),
            dimensions=self.settings.rag_embedding_dimensions,
        )

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
                document = RAGDocument(
                    ticker=ticker,
                    source="SEC EDGAR",
                    title=f"{ticker} latest SEC {filing.form}",
                    text=filing.text,
                    url=filing.url,
                    date=filing.filing_date,
                    metadata={"form": filing.form, "cik": filing.cik, "source_status": "SEC EDGAR"},
                )
                evidence, diagnostics = self.pipeline.ingest_and_retrieve([document], topics=topics, top_k_per_topic=1)
                return FilingRAGResult(
                    ticker=ticker,
                    evidence=evidence,
                    citations=[item.citation for item in evidence],
                    source_status="SEC EDGAR",
                    diagnostics=diagnostics,
                )

        company = get_demo_company(ticker)
        filing_text, filing_path = load_filing_text(ticker)
        document = RAGDocument(
            ticker=company["ticker"],
            source="CapitalLens Sample Filing Corpus",
            title=f"{company['company_name']} filing excerpt",
            text=filing_text,
            url=f"data/sample_filings/{filing_path.name}",
            date="2026-06-14",
            metadata={"company_name": company["company_name"], "source_status": "demo filings"},
        )
        evidence, diagnostics = self.pipeline.ingest_and_retrieve([document], topics=topics, top_k_per_topic=1)
        return FilingRAGResult(
            ticker=company["ticker"],
            evidence=evidence,
            citations=[item.citation for item in evidence],
            source_status="demo filings",
            diagnostics=diagnostics,
        )
