"""News retrieval tools with provider hooks and demo fallback."""

from __future__ import annotations

import logging
from typing import Any

from app.config import Settings, get_settings
from app.schemas.models import Citation, NewsItem, NewsSummary
from app.tools.finance_tools import get_demo_company, resolve_ticker

logger = logging.getLogger(__name__)


def _demo_news(query: str) -> NewsSummary:
    company = get_demo_company(query)
    citations: list[Citation] = []
    items: list[NewsItem] = []
    for idx, item in enumerate(company.get("news", []), start=1):
        citation_id = f"news-{company['ticker']}-{idx}"
        citations.append(
            Citation(
                id=citation_id,
                source=item["source"],
                title=item["title"],
                url=item.get("url"),
                date=item.get("date"),
                snippet=item["summary"],
            )
        )
        items.append(NewsItem(**item, citation_id=citation_id))

    negative = sum(1 for item in items if item.impact == "negative")
    positive = sum(1 for item in items if item.impact == "positive")
    tone = "negative" if negative > positive else "positive" if positive > negative else "neutral"
    return NewsSummary(ticker=company["ticker"], items=items, overall_tone=tone, citations=citations)


def _fetch_newsapi(query: str, settings: Settings) -> NewsSummary | None:
    if not settings.news_api_key:
        return None
    try:
        import requests  # type: ignore
    except ImportError:
        logger.info("requests is not installed; using demo news.")
        return None

    try:  # pragma: no cover - network-dependent optional adapter
        company = get_demo_company(query)
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": f"{company['company_name']} stock OR earnings OR business",
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 5,
                "apiKey": settings.news_api_key,
            },
            timeout=8,
        )
        response.raise_for_status()
        articles: list[dict[str, Any]] = response.json().get("articles", [])
        if not articles:
            return None
        citations: list[Citation] = []
        items: list[NewsItem] = []
        for idx, article in enumerate(articles, start=1):
            description = article.get("description") or article.get("content") or "News item retrieved from provider."
            title = article.get("title") or f"{company['company_name']} news"
            citation_id = f"news-{company['ticker']}-{idx}"
            impact = "negative" if any(term in f"{title} {description}".lower() for term in ["probe", "lawsuit", "miss", "decline", "risk"]) else "neutral"
            citations.append(
                Citation(
                    id=citation_id,
                    source=(article.get("source") or {}).get("name") or "NewsAPI",
                    title=title,
                    url=article.get("url"),
                    date=(article.get("publishedAt") or "")[:10],
                    snippet=description[:300],
                )
            )
            items.append(
                NewsItem(
                    title=title,
                    source=(article.get("source") or {}).get("name") or "NewsAPI",
                    date=(article.get("publishedAt") or "")[:10],
                    summary=description[:500],
                    impact=impact,  # simple provider-side triage; ReportAgent adds nuance.
                    url=article.get("url"),
                    citation_id=citation_id,
                )
            )
        negative = sum(1 for item in items if item.impact == "negative")
        tone = "negative" if negative >= 2 else "neutral"
        return NewsSummary(ticker=company["ticker"], items=items, overall_tone=tone, citations=citations)
    except Exception as exc:
        logger.warning("NewsAPI fetch failed for %s: %s", query, exc)
        return None


def fetch_recent_news(query: str, settings: Settings | None = None) -> NewsSummary:
    settings = settings or get_settings()
    ticker = resolve_ticker(query)
    if not settings.demo_mode:
        live = _fetch_newsapi(ticker, settings)
        if live:
            return live
    return _demo_news(ticker)

