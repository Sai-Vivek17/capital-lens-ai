"""NewsAgent."""

from __future__ import annotations

from app.config import Settings
from app.schemas.models import NewsSummary
from app.tools.news_tools import fetch_recent_news


class NewsAgent:
    name = "NewsAgent"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(self, query: str) -> NewsSummary:
        return fetch_recent_news(query, settings=self.settings)

