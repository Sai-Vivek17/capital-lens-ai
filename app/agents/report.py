"""ReportAgent turns structured outputs into an analyst-style memo."""

from __future__ import annotations

import logging
from datetime import date

from app.config import Settings
from app.schemas.models import Citation, ReportOutput, ResearchBundle
from app.tools.finance_tools import format_money, pct

logger = logging.getLogger(__name__)


class ReportAgent:
    name = "ReportAgent"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(self, bundle: ResearchBundle) -> ReportOutput:
        markdown = self._compose_markdown(bundle)
        markdown = self._optional_llm_polish(markdown)
        citations = self._collect_citations(bundle)
        return ReportOutput(
            ticker=bundle.market_data.ticker,
            company_name=bundle.market_data.company_name,
            mode=bundle.request.mode,
            markdown=markdown,
            citations=citations,
            scores=bundle.scores,
        )

    def _compose_markdown(self, bundle: ResearchBundle) -> str:
        market = bundle.market_data
        metrics = market.metrics
        news = bundle.news
        filing = bundle.filing_rag
        risks = bundle.risks
        valuation = bundle.valuation
        scores = bundle.scores
        market_cite = market.citations[0].id if market.citations else "market-data"
        filing_cite = filing.citations[0].id if filing.citations else market_cite

        recent_developments = "\n".join(
            f"- **{item.title}** ({item.date}, {item.impact}): {item.summary} [{item.citation_id or 'news'}]"
            for item in news.items
        ) or "- No recent business news was available from configured sources."

        financial_lines = [
            f"- Revenue TTM: **{format_money(metrics.revenue_ttm, metrics.currency)}** [{market_cite}]",
            f"- Net income TTM: **{format_money(metrics.net_income_ttm, metrics.currency)}** [{market_cite}]",
            f"- Free cash flow TTM: **{format_money(metrics.free_cash_flow_ttm, metrics.currency)}** [{market_cite}]",
            f"- Gross margin: **{pct(metrics.gross_margin)}**; operating margin: **{pct(metrics.operating_margin)}** [{market_cite}]",
            f"- Revenue growth: **{pct(metrics.revenue_growth)}**; profit growth: **{pct(metrics.profit_growth)}** [{market_cite}]",
        ]

        valuation_lines = "\n".join(f"- {item.name}: **{item.value}**. {item.interpretation} [{market_cite}]" for item in valuation.metrics)
        risk_lines = "\n".join(
            f"- **{risk.category} ({risk.severity}/5):** {risk.description} Evidence: {risk.evidence} [{risk.citation_id or market_cite}]"
            for risk in risks.risks
        )
        source_lines = "\n".join(f"- [{citation.id}] {citation.title} - {citation.source}" + (f" ({citation.url})" if citation.url else "") for citation in self._collect_citations(bundle))
        rag_note = self._rag_note(bundle)

        bull_case = self._bull_case(bundle, market_cite, filing_cite)
        bear_case = self._bear_case(bundle, market_cite)
        conclusion = self._conclusion(bundle)

        return f"""# CapitalLens AI Research Memo

Company: {market.company_name}  
Ticker: {market.ticker}  
Date: {date.today().isoformat()}  
Research Mode: {bundle.request.mode}

## 1. Executive Summary
{market.company_name} is a {market.sector or "listed"} company in {market.industry or "its reported industry"}. {market.description} [{market_cite}]

CapitalLens scores this research set as **Financial Health {scores.financial_health}/100**, **Risk {scores.risk}/100**, **Momentum {scores.momentum}/100**, with **{scores.confidence}** overall research confidence. The current profile suggests {conclusion}

## 2. Business Overview
{market.description} Filing evidence indicates that business quality depends on revenue durability, competitive position, execution discipline, and regulatory context. [{filing_cite}]

{rag_note}

## 3. Recent Developments
{recent_developments}

## 4. Financial Health
{chr(10).join(financial_lines)}

Financial health score: **{scores.financial_health}/100**. This score blends profitability, growth, liquidity, leverage, and cash-flow availability.

## 5. Valuation Snapshot
{valuation_lines}

Peer context: {valuation.summary}

## 6. Key Risks
Risk score: **{risks.risk_score}/100**. {risks.summary}

{risk_lines}

## 7. Bull Case
{bull_case}

## 8. Bear Case
{bear_case}

## 9. Agent Conclusion
{conclusion} This is not a personalized trading recommendation. A prudent next step would be to validate live filings, management commentary, segment-level trends, and valuation assumptions before making any financial decision.

## 10. Sources & Citations
{source_lines}

## Disclaimer
CapitalLens AI is for research and educational purposes only. It may contain errors, stale data, simplified assumptions, or incomplete source coverage. It does not provide personalized investment, legal, accounting, tax, or trading advice.
"""

    @staticmethod
    def _bull_case(bundle: ResearchBundle, market_cite: str, filing_cite: str) -> str:
        market = bundle.market_data
        positives = [item.summary for item in bundle.news.items if item.impact == "positive"]
        growth = market.metrics.revenue_growth or 0
        margin = market.metrics.operating_margin or 0
        parts = []
        if growth > 0.08:
            parts.append(f"Revenue growth of {growth * 100:.1f}% supports the view that demand remains healthy [{market_cite}].")
        if margin > 0.20:
            parts.append(f"Operating margin of {margin * 100:.1f}% points to meaningful profitability and operating leverage [{market_cite}].")
        if positives:
            parts.append(f"Recent positive signals include: {positives[0]}")
        parts.append(f"Filing evidence supports the presence of strategic assets or market positioning that could reinforce durability [{filing_cite}].")
        return " ".join(parts)

    @staticmethod
    def _bear_case(bundle: ResearchBundle, market_cite: str) -> str:
        negatives = [item.summary for item in bundle.news.items if item.impact == "negative"]
        top_risks = sorted(bundle.risks.risks, key=lambda item: item.severity, reverse=True)[:2]
        parts = []
        if negatives:
            parts.append(f"Recent negative signal: {negatives[0]}")
        for risk in top_risks:
            parts.append(f"{risk.category} risk is rated {risk.severity}/5 because {risk.description} [{risk.citation_id or market_cite}].")
        return " ".join(parts) or f"Key downside depends on execution quality, market conditions, and valuation sensitivity [{market_cite}]."

    @staticmethod
    def _conclusion(bundle: ResearchBundle) -> str:
        scores = bundle.scores
        if scores.financial_health >= 75 and scores.risk < 55 and scores.momentum >= 55:
            return "the company appears fundamentally resilient, though valuation and source freshness still require review."
        if scores.risk >= 70:
            return "the company requires caution because the downside signals are prominent relative to the available evidence."
        if scores.financial_health < 50:
            return "the company needs further review because financial quality indicators are mixed or weak."
        return "the company presents a balanced research profile with identifiable strengths and watch items."

    @staticmethod
    def _rag_note(bundle: ResearchBundle) -> str:
        diagnostics = bundle.filing_rag.diagnostics
        if diagnostics is None:
            return "**RAG Source Integrity:** Retrieval diagnostics were unavailable for this run."
        return (
            "**RAG Source Integrity:** "
            f"Strategy `{diagnostics.retrieval_strategy}` indexed {diagnostics.indexed_documents} document(s) "
            f"and {diagnostics.indexed_chunks} chunk(s). Citation coverage is "
            f"{diagnostics.citation_coverage * 100:.0f}% with {diagnostics.coverage} evidence coverage."
        )

    def _optional_llm_polish(self, markdown: str) -> str:
        if self.settings.demo_mode or not self.settings.openai_api_key:
            return markdown
        try:  # pragma: no cover - optional LLM path
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=self.settings.openai_api_key)
            response = client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You polish financial research memos. Preserve all citations, scores, section headings, and safety disclaimers. Do not add unsupported facts.",
                    },
                    {"role": "user", "content": markdown},
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content
            return content or markdown
        except Exception as exc:
            logger.warning("LLM polish failed; using deterministic report: %s", exc)
            return markdown

    @staticmethod
    def _collect_citations(bundle: ResearchBundle) -> list[Citation]:
        citations: dict[str, Citation] = {}
        for citation in [*bundle.market_data.citations, *bundle.news.citations, *bundle.filing_rag.citations]:
            citations[citation.id] = citation
        return list(citations.values())
