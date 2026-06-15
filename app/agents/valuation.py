"""ValuationAgent creates a lightweight valuation snapshot."""

from __future__ import annotations

from statistics import median

from app.schemas.models import MarketData, PeerComparison, ValuationMetric, ValuationSnapshot
from app.tools.finance_tools import get_demo_peers


class ValuationAgent:
    name = "ValuationAgent"

    def run(self, market: MarketData) -> ValuationSnapshot:
        peers = get_demo_peers(market.ticker)
        metrics = market.metrics
        valuation_metrics = [
            ValuationMetric(name="P/E", value=self._value(metrics.pe_ratio), interpretation=self._interpret_multiple("P/E", metrics.pe_ratio, [peer.pe_ratio for peer in peers])),
            ValuationMetric(name="P/S", value=self._value(metrics.ps_ratio), interpretation=self._interpret_multiple("P/S", metrics.ps_ratio, [peer.ps_ratio for peer in peers])),
            ValuationMetric(name="EV/EBITDA", value=self._value(metrics.ev_ebitda), interpretation=self._interpret_multiple("EV/EBITDA", metrics.ev_ebitda, [peer.ev_ebitda for peer in peers])),
            ValuationMetric(name="Market Cap", value=metrics.market_cap, interpretation="Scale indicator; compare with revenue, cash flow, and growth durability."),
        ]
        summary = self._summary(metrics.pe_ratio, metrics.ps_ratio, peers)
        return ValuationSnapshot(ticker=market.ticker, metrics=valuation_metrics, peers=peers, summary=summary)

    @staticmethod
    def _value(value: float | None) -> float | str:
        return round(value, 2) if value is not None else "Unavailable"

    @staticmethod
    def _interpret_multiple(name: str, value: float | None, peer_values: list[float | None]) -> str:
        clean_peers = [item for item in peer_values if item is not None]
        if value is None:
            return f"{name} unavailable from current data; avoid inferring valuation from missing inputs."
        if not clean_peers:
            return f"{name} available, but peer median is unavailable."
        peer_median = median(clean_peers)
        if value > peer_median * 1.25:
            return f"Premium to peer median of {peer_median:.1f}; requires stronger growth, margins, or strategic optionality."
        if value < peer_median * 0.75:
            return f"Discount to peer median of {peer_median:.1f}; may reflect lower growth, cyclicality, or underappreciated value."
        return f"Near peer median of {peer_median:.1f}; valuation argument likely depends on quality and trend evidence."

    @staticmethod
    def _summary(pe: float | None, ps: float | None, peers: list[PeerComparison]) -> str:
        if pe is None and ps is None:
            return "Key valuation multiples are unavailable, so the snapshot should be treated as incomplete."
        premium_flags = 0
        peer_pe = [peer.pe_ratio for peer in peers if peer.pe_ratio is not None]
        peer_ps = [peer.ps_ratio for peer in peers if peer.ps_ratio is not None]
        if pe is not None and peer_pe and pe > median(peer_pe) * 1.25:
            premium_flags += 1
        if ps is not None and peer_ps and ps > median(peer_ps) * 1.25:
            premium_flags += 1
        if premium_flags >= 2:
            return "The company screens at a valuation premium to available peers; the memo should test whether growth and durability justify it."
        if premium_flags == 1:
            return "Valuation is mixed, with at least one premium metric that deserves closer peer and growth analysis."
        return "Valuation appears broadly reasonable versus the simple peer set, subject to data limitations and business-quality differences."

