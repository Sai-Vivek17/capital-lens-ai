"""Best-effort SEC/EDGAR helpers for live US filing retrieval."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

KNOWN_CIKS = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "TSLA": "0001318605",
}


@dataclass(frozen=True)
class FilingText:
    ticker: str
    cik: str
    form: str
    filing_date: str
    url: str
    text: str


def fetch_latest_10k_text(ticker: str, settings: Settings | None = None) -> FilingText | None:
    """Fetch the latest 10-K text for known US demo tickers.

    This adapter is intentionally conservative: if SEC access fails, parsing is
    blocked, or the ticker is non-US, callers should use the local filing corpus.
    """

    settings = settings or get_settings()
    normalized = ticker.upper()
    cik = KNOWN_CIKS.get(normalized)
    if not cik:
        return None

    try:
        import requests  # type: ignore
    except ImportError:
        return None

    headers = {"User-Agent": settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"}
    submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:  # pragma: no cover - network-dependent
        submission = requests.get(submissions_url, headers=headers, timeout=10)
        submission.raise_for_status()
        recent = submission.json().get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession_numbers = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        filing_dates = recent.get("filingDate", [])
        for idx, form in enumerate(forms):
            if form != "10-K":
                continue
            accession = accession_numbers[idx]
            primary_doc = primary_docs[idx]
            filing_date = filing_dates[idx]
            accession_path = accession.replace("-", "")
            cik_path = str(int(cik))
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_path}/{accession_path}/{primary_doc}"
            filing_response = requests.get(filing_url, headers=headers, timeout=15)
            filing_response.raise_for_status()
            text = _clean_sec_text(filing_response.text)
            if len(text) > 2_000:
                return FilingText(ticker=normalized, cik=cik, form=form, filing_date=filing_date, url=filing_url, text=text[:120_000])
    except Exception as exc:
        logger.warning("SEC filing fetch failed for %s: %s", ticker, exc)
    return None


def _clean_sec_text(raw: str) -> str:
    raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = raw.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", raw).strip()

