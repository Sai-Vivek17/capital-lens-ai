from __future__ import annotations

from app.config import Settings
from app.tools.finance_tools import fetch_market_data, resolve_ticker, validate_ticker


def test_ticker_validation_and_alias_resolution() -> None:
    assert validate_ticker("AAPL")
    assert validate_ticker("RELIANCE.NS")
    assert resolve_ticker("Tesla") == "TSLA"
    assert resolve_ticker("Tata Consultancy Services") == "TCS.NS"
    assert not validate_ticker("not a ticker with spaces", allow_alias=False)


def test_demo_financial_metric_extraction() -> None:
    market = fetch_market_data("MSFT", Settings(demo_mode=True))
    assert market.ticker == "MSFT"
    assert market.company_name == "Microsoft Corporation"
    assert market.metrics.revenue_ttm and market.metrics.revenue_ttm > 0
    assert market.metrics.pe_ratio and market.metrics.pe_ratio > 0
    assert len(market.price_history) >= 6
    assert market.citations

