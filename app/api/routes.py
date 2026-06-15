"""HTTP API for CapitalLens AI."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.main import CapitalLensOrchestrator
from app.schemas.models import ResearchRequest, ResearchResult, WatchlistItem, WatchlistScanResult
from app.storage.database import add_watchlist_ticker, list_recent_alerts, list_watchlist, remove_watchlist_ticker
from app.tools.finance_tools import TickerValidationError

router = APIRouter()


@router.post("/research", response_model=ResearchResult)
def research(request: ResearchRequest) -> ResearchResult:
    try:
        return CapitalLensOrchestrator().run_research(request)
    except TickerValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Research run failed: {exc}") from exc


@router.get("/watchlist", response_model=list[WatchlistItem])
def get_watchlist() -> list[WatchlistItem]:
    return list_watchlist()


@router.post("/watchlist/scan", response_model=list[WatchlistScanResult])
def scan_watchlist() -> list[WatchlistScanResult]:
    return CapitalLensOrchestrator().scan_watchlist()


@router.get("/watchlist/alerts")
def alerts():
    return list_recent_alerts()


@router.post("/watchlist/{ticker}", response_model=WatchlistItem)
def add_watchlist(ticker: str) -> WatchlistItem:
    try:
        return add_watchlist_ticker(ticker)
    except TickerValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/watchlist/{ticker}")
def delete_watchlist(ticker: str) -> dict[str, str]:
    remove_watchlist_ticker(ticker)
    return {"status": "removed", "ticker": ticker}
