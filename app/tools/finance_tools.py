"""Market data tools with live adapters and deterministic demo fallback."""

from __future__ import annotations

import json
import logging
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import DATA_DIR, Settings, get_settings
from app.schemas.models import Citation, FinancialMetrics, FinancialTrendPoint, MarketData, PeerComparison, PricePoint

logger = logging.getLogger(__name__)

TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,14}$")


class TickerValidationError(ValueError):
    """Raised when a ticker or company query cannot be resolved."""


@lru_cache(maxsize=1)
def load_demo_companies() -> dict[str, dict[str, Any]]:
    path = DATA_DIR / "demo_companies.json"
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_query(query: str) -> str:
    return query.strip().upper().replace(" ", "")


def resolve_ticker(query: str) -> str:
    """Resolve a ticker or company name against demo aliases before validating."""

    normalized = normalize_query(query)
    companies = load_demo_companies()
    if normalized in companies:
        return normalized

    compact = re.sub(r"[^A-Z0-9.]", "", query.upper())
    for ticker, company in companies.items():
        aliases = [company.get("company_name", ""), *company.get("aliases", [])]
        normalized_aliases = {re.sub(r"[^A-Z0-9.]", "", alias.upper()) for alias in aliases}
        if compact in normalized_aliases:
            return ticker

    if validate_ticker(normalized, allow_alias=False):
        return normalized
    raise TickerValidationError(f"Could not resolve '{query}' as a supported ticker or company name.")


def validate_ticker(query: str, allow_alias: bool = True) -> bool:
    try:
        ticker = resolve_ticker(query) if allow_alias else query.strip().upper()
    except TickerValidationError:
        return False
    return bool(TICKER_PATTERN.match(ticker))


def get_demo_company(query: str) -> dict[str, Any]:
    ticker = resolve_ticker(query)
    companies = load_demo_companies()
    if ticker not in companies:
        raise TickerValidationError(f"No demo data is available for '{query}'.")
    return companies[ticker]


def _demo_market_citation(ticker: str, company_name: str) -> Citation:
    return Citation(
        id=f"market-{ticker}",
        source="CapitalLens Demo Dataset",
        title=f"{company_name} demo financial snapshot",
        url="data/demo_companies.json",
        date="2026-06-14",
        snippet="Deterministic sample metrics used when live market data or API keys are unavailable.",
    )


def build_market_data_from_demo(query: str) -> MarketData:
    company = get_demo_company(query)
    metrics = FinancialMetrics(currency=company["currency"], **company["metrics"])
    citation = _demo_market_citation(company["ticker"], company["company_name"])
    return MarketData(
        ticker=company["ticker"],
        company_name=company["company_name"],
        exchange=company.get("exchange"),
        sector=company.get("sector"),
        industry=company.get("industry"),
        description=company.get("description", ""),
        metrics=metrics,
        price_history=[PricePoint(**point) for point in company.get("price_history", [])],
        financial_trends=[FinancialTrendPoint(**point) for point in company.get("financial_trends", [])],
        data_quality="High",
        source="demo",
        citations=[citation],
    )


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        numeric = float(value)
        if math.isnan(numeric) or math.isinf(numeric):
            return None
        return numeric
    except (TypeError, ValueError):
        return None


def _fetch_live_yfinance(ticker: str) -> MarketData | None:
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        logger.info("yfinance is not installed; using demo data.")
        return None

    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info or {}
        history = yf_ticker.history(period="1y", interval="1mo")
        if not info and history.empty:
            return None

        price_history: list[PricePoint] = []
        if not history.empty:
            for idx, row in history.tail(12).iterrows():
                price_history.append(PricePoint(date=str(idx.date()), close=float(row["Close"])))

        financials = []
        try:
            annuals = yf_ticker.financials
            if annuals is not None and not annuals.empty:
                for period in list(annuals.columns[:4])[::-1]:
                    financials.append(
                        FinancialTrendPoint(
                            period=str(period.date() if hasattr(period, "date") else period),
                            revenue=_safe_float(annuals.get(period, {}).get("Total Revenue")),
                            net_income=_safe_float(annuals.get(period, {}).get("Net Income")),
                        )
                    )
        except Exception as exc:  # pragma: no cover - live adapter best effort
            logger.warning("Could not fetch yfinance financial trends for %s: %s", ticker, exc)

        company_name = info.get("longName") or info.get("shortName") or ticker
        currency = info.get("currency") or "USD"
        metrics = FinancialMetrics(
            currency=currency,
            price=_safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
            previous_close=_safe_float(info.get("previousClose")),
            market_cap=_safe_float(info.get("marketCap")),
            enterprise_value=_safe_float(info.get("enterpriseValue")),
            revenue_ttm=_safe_float(info.get("totalRevenue")),
            net_income_ttm=_safe_float(info.get("netIncomeToCommon")),
            free_cash_flow_ttm=_safe_float(info.get("freeCashflow")),
            gross_margin=_safe_float(info.get("grossMargins")),
            operating_margin=_safe_float(info.get("operatingMargins")),
            revenue_growth=_safe_float(info.get("revenueGrowth")),
            profit_growth=_safe_float(info.get("earningsGrowth")),
            pe_ratio=_safe_float(info.get("trailingPE")),
            ps_ratio=_safe_float(info.get("priceToSalesTrailing12Months")),
            ev_ebitda=_safe_float(info.get("enterpriseToEbitda")),
            debt_to_equity=_safe_float(info.get("debtToEquity")),
            current_ratio=_safe_float(info.get("currentRatio")),
            beta=_safe_float(info.get("beta")),
            fifty_two_week_high=_safe_float(info.get("fiftyTwoWeekHigh")),
            fifty_two_week_low=_safe_float(info.get("fiftyTwoWeekLow")),
        )
        citation = Citation(
            id=f"market-{ticker}",
            source="Yahoo Finance via yfinance",
            title=f"{company_name} market data",
            url=f"https://finance.yahoo.com/quote/{ticker}",
            snippet="Market and financial data fetched through yfinance.",
        )
        return MarketData(
            ticker=ticker,
            company_name=company_name,
            exchange=info.get("exchange"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            description=info.get("longBusinessSummary", ""),
            metrics=metrics,
            price_history=price_history,
            financial_trends=financials,
            data_quality="Medium",
            source="yfinance",
            citations=[citation],
        )
    except Exception as exc:  # pragma: no cover - network-dependent
        logger.warning("Live market fetch failed for %s: %s", ticker, exc)
        return None


def fetch_market_data(query: str, settings: Settings | None = None) -> MarketData:
    """Fetch market data, falling back to demo data whenever live data is unavailable."""

    settings = settings or get_settings()
    ticker = resolve_ticker(query)
    if not settings.demo_mode:
        live = _fetch_live_yfinance(ticker)
        if live:
            return live

    try:
        return build_market_data_from_demo(ticker)
    except TickerValidationError:
        if settings.demo_mode:
            raise
        raise TickerValidationError(
            f"No live or demo data was found for '{query}'. Try AAPL, MSFT, TSLA, RELIANCE.NS, or TCS.NS."
        )


def get_demo_peers(ticker: str) -> list[PeerComparison]:
    try:
        company = get_demo_company(ticker)
    except TickerValidationError:
        return []
    return [PeerComparison(**peer) for peer in company.get("peers", [])]


def format_money(value: float | None, currency: str = "USD") -> str:
    if value is None:
        return "Unavailable"
    abs_value = abs(value)
    if abs_value >= 1_000_000_000_000:
        return f"{currency} {value / 1_000_000_000_000:.2f}T"
    if abs_value >= 1_000_000_000:
        return f"{currency} {value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"{currency} {value / 1_000_000:.2f}M"
    return f"{currency} {value:,.2f}"


def pct(value: float | None) -> str:
    if value is None:
        return "Unavailable"
    return f"{value * 100:.1f}%"


def calculate_price_change_pct(history: list[PricePoint]) -> float | None:
    if len(history) < 2:
        return None
    previous = history[-2].close
    latest = history[-1].close
    if previous == 0:
        return None
    return (latest - previous) / previous * 100


def calculate_volatility(history: list[PricePoint]) -> float | None:
    if len(history) < 3:
        return None
    returns = []
    for before, after in zip(history, history[1:]):
        if before.close:
            returns.append((after.close - before.close) / before.close)
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((item - mean) ** 2 for item in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(12) * 100


def data_file_exists(path: Path) -> bool:
    return path.exists() and path.is_file()

