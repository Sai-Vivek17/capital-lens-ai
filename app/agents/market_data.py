"""MarketDataAgent."""

from __future__ import annotations

from app.config import Settings
from app.schemas.models import MarketData
from app.tools.finance_tools import fetch_market_data


class MarketDataAgent:
    name = "MarketDataAgent"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(self, query: str) -> MarketData:
        return fetch_market_data(query, settings=self.settings)

