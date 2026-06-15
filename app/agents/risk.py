"""RiskAgent turns structured evidence into an interpretable risk matrix."""

from __future__ import annotations

from app.schemas.models import FilingRAGResult, MarketData, NewsSummary, RiskItem, RiskMatrix
from app.tools.finance_tools import calculate_volatility


class RiskAgent:
    name = "RiskAgent"

    def run(self, market: MarketData, news: NewsSummary, filing: FilingRAGResult | None = None) -> RiskMatrix:
        metrics = market.metrics
        risks: list[RiskItem] = []

        if metrics.pe_ratio is not None:
            if metrics.pe_ratio >= 60:
                risks.append(self._risk("Valuation", f"P/E of {metrics.pe_ratio:.1f} is high versus broad-market norms.", 5, "Elevated valuation multiple can amplify downside if growth disappoints.", market.citations[0].id))
            elif metrics.pe_ratio >= 35:
                risks.append(self._risk("Valuation", f"P/E of {metrics.pe_ratio:.1f} requires durable growth and margin execution.", 4, "Premium multiples leave less room for execution misses.", market.citations[0].id))
            elif metrics.pe_ratio >= 25:
                risks.append(self._risk("Valuation", f"P/E of {metrics.pe_ratio:.1f} is above value-oriented thresholds.", 3, "Multiple is not extreme but should be compared with growth quality.", market.citations[0].id))

        if metrics.ps_ratio is not None and metrics.ps_ratio >= 10:
            risks.append(self._risk("Valuation", f"P/S of {metrics.ps_ratio:.1f} implies high expectations for revenue durability.", 4, "High sales multiple increases sensitivity to revenue deceleration.", market.citations[0].id))

        if metrics.operating_margin is not None and metrics.operating_margin < 0.10:
            risks.append(self._risk("Financial", f"Operating margin of {metrics.operating_margin * 100:.1f}% leaves limited cushion.", 4, "Thin margins can pressure earnings during pricing or cost shocks.", market.citations[0].id))
        elif metrics.operating_margin is not None and metrics.operating_margin < 0.18:
            risks.append(self._risk("Financial", f"Operating margin of {metrics.operating_margin * 100:.1f}% is moderate for the business mix.", 3, "Profitability should be monitored against peers and prior periods.", market.citations[0].id))

        if metrics.profit_growth is not None and metrics.profit_growth < -0.15:
            risks.append(self._risk("Financial", f"Profit growth is negative at {metrics.profit_growth * 100:.1f}%.", 4, "Falling profit can weaken valuation support and sentiment.", market.citations[0].id))
        elif metrics.profit_growth is not None and metrics.profit_growth < 0:
            risks.append(self._risk("Financial", f"Profit growth is slightly negative at {metrics.profit_growth * 100:.1f}%.", 3, "Earnings trend needs confirmation in future periods.", market.citations[0].id))

        if metrics.debt_to_equity is not None:
            debt_ratio = metrics.debt_to_equity / 100 if metrics.debt_to_equity > 10 else metrics.debt_to_equity
            if debt_ratio > 1.2:
                risks.append(self._risk("Balance Sheet", f"Debt-to-equity of {metrics.debt_to_equity:.2f} indicates meaningful leverage.", 4, "Leverage can reduce flexibility if earnings or cash flow weaken.", market.citations[0].id))
            elif debt_ratio > 0.6:
                risks.append(self._risk("Balance Sheet", f"Debt-to-equity of {metrics.debt_to_equity:.2f} is manageable but relevant.", 3, "Leverage should be assessed alongside cash flow durability.", market.citations[0].id))

        if metrics.current_ratio is not None and metrics.current_ratio < 1.0:
            risks.append(self._risk("Liquidity", f"Current ratio of {metrics.current_ratio:.2f} is below 1.0.", 3, "Short-term obligations exceed short-term assets on this metric.", market.citations[0].id))

        if metrics.beta is not None and metrics.beta >= 1.5:
            risks.append(self._risk("Market", f"Beta of {metrics.beta:.2f} points to high market sensitivity.", 4, "Higher beta can create sharper drawdowns in risk-off periods.", market.citations[0].id))

        volatility = calculate_volatility(market.price_history)
        if volatility is not None and volatility >= 40:
            risks.append(self._risk("Market", f"Estimated annualized volatility is {volatility:.1f}%.", 4, "Recent price path suggests elevated trading variability.", market.citations[0].id))
        elif volatility is not None and volatility >= 25:
            risks.append(self._risk("Market", f"Estimated annualized volatility is {volatility:.1f}%.", 3, "Volatility is a watch item for position sizing and timing research.", market.citations[0].id))

        for item in news.items:
            if item.impact == "negative":
                risks.append(self._risk("News/Event", item.summary, 3, f"Recent negative development: {item.title}.", item.citation_id))

        if filing:
            for evidence in filing.evidence:
                topic_text = f"{evidence.topic} {evidence.claim}".lower()
                if any(term in topic_text for term in ["regulatory", "legal", "compliance"]):
                    risks.append(self._risk("Regulatory", evidence.claim, 3, "Filing evidence identifies regulatory or compliance exposure.", evidence.citation.id))
                elif any(term in topic_text for term in ["competition", "competitive"]):
                    risks.append(self._risk("Competitive", evidence.claim, 3, "Filing evidence highlights competitive pressure or differentiation needs.", evidence.citation.id))
                elif any(term in topic_text for term in ["debt", "liquidity", "cash flow"]):
                    risks.append(self._risk("Liquidity", evidence.claim, 2, "Filing evidence relates to funding, liquidity, or capital discipline.", evidence.citation.id))

        if not risks:
            risks.append(self._risk("General", "No severe risk trigger was detected from available demo signals.", 2, "Absence of detected risk is not the same as absence of risk.", market.citations[0].id if market.citations else None))

        risk_score = self._aggregate_score(risks)
        summary = self._summary(risk_score)
        return RiskMatrix(ticker=market.ticker, risks=risks[:10], risk_score=risk_score, summary=summary)

    @staticmethod
    def _risk(category: str, description: str, severity: int, evidence: str, citation_id: str | None = None) -> RiskItem:
        return RiskItem(category=category, description=description, severity=max(1, min(5, severity)), evidence=evidence, citation_id=citation_id)

    @staticmethod
    def _aggregate_score(risks: list[RiskItem]) -> int:
        if not risks:
            return 0
        weighted = sum(risk.severity * (1.25 if risk.category in {"Valuation", "Financial", "Balance Sheet"} else 1.0) for risk in risks)
        max_weighted = len(risks) * 5 * 1.25
        return int(round(max(0, min(100, weighted / max_weighted * 100))))

    @staticmethod
    def _summary(score: int) -> str:
        if score >= 70:
            return "High risk profile; downside and evidence quality should be reviewed carefully."
        if score >= 45:
            return "Moderate risk profile with several watch items that warrant follow-up."
        return "Lower detected risk profile based on available structured signals, with normal diligence still required."

