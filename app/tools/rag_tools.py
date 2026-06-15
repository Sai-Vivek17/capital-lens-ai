"""RAG utilities for filing excerpts.

The production path can be upgraded to ChromaDB by installing the dependency.
For reliable local demos and tests, this module ships a deterministic lexical
vector index that exposes the same retrieve-style behavior.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app.config import DATA_DIR
from app.schemas.models import Citation, FilingEvidence
from app.tools.finance_tools import get_demo_company

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9\-]{2,}")


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    source_path: Path


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def chunk_text(text: str, max_words: int = 85) -> list[str]:
    paragraphs = [item.strip() for item in text.split("\n\n") if item.strip()]
    chunks: list[str] = []
    for paragraph in paragraphs:
        words = paragraph.split()
        if len(words) <= max_words:
            chunks.append(paragraph)
            continue
        for start in range(0, len(words), max_words):
            chunks.append(" ".join(words[start : start + max_words]))
    return chunks


class SimpleVectorIndex:
    """Tiny TF-IDF-like retriever used when ChromaDB is unavailable."""

    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.term_counts = [Counter(tokenize(chunk.text)) for chunk in chunks]
        self.doc_freq = Counter()
        for counts in self.term_counts:
            for term in counts:
                self.doc_freq[term] += 1

    def _score(self, query: str, idx: int) -> float:
        query_terms = Counter(tokenize(query))
        if not query_terms:
            return 0.0
        counts = self.term_counts[idx]
        score = 0.0
        total_docs = max(len(self.chunks), 1)
        for term, q_count in query_terms.items():
            if term not in counts:
                continue
            idf = math.log((1 + total_docs) / (1 + self.doc_freq[term])) + 1
            score += q_count * counts[term] * idf
        norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
        return score / norm

    def search(self, query: str, top_k: int = 3) -> list[tuple[Chunk, float]]:
        scored = [(chunk, self._score(query, idx)) for idx, chunk in enumerate(self.chunks)]
        scored.sort(key=lambda item: item[1], reverse=True)
        return [(chunk, score) for chunk, score in scored[:top_k] if score > 0]


def filing_path_for_ticker(ticker: str) -> Path:
    company = get_demo_company(ticker)
    return DATA_DIR / "sample_filings" / company["filing_file"]


def load_filing_text(ticker: str) -> tuple[str, Path]:
    path = filing_path_for_ticker(ticker)
    if not path.exists():
        raise FileNotFoundError(f"No sample filing was found for {ticker}: {path}")
    return path.read_text(encoding="utf-8"), path


def build_index_from_text(ticker: str, text: str, source_path: Path) -> SimpleVectorIndex:
    chunks = [Chunk(id=f"{ticker}-filing-{idx}", text=chunk, source_path=source_path) for idx, chunk in enumerate(chunk_text(text), start=1)]
    return SimpleVectorIndex(chunks)


def build_index_for_ticker(ticker: str) -> SimpleVectorIndex:
    text, path = load_filing_text(ticker)
    return build_index_from_text(ticker, text, path)


def retrieve_filing_evidence(ticker: str, topics: list[str], top_k_per_topic: int = 1) -> list[FilingEvidence]:
    company = get_demo_company(ticker)
    index = build_index_for_ticker(company["ticker"])
    return _retrieve_from_index(
        ticker=company["ticker"],
        company_name=company["company_name"],
        index=index,
        topics=topics,
        top_k_per_topic=top_k_per_topic,
        source_title=f"{company['company_name']} filing excerpt",
        source_url=None,
        source_date="2026-06-14",
    )


def retrieve_filing_evidence_from_text(
    ticker: str,
    company_name: str,
    text: str,
    topics: list[str],
    source_url: str,
    source_title: str,
    source_date: str | None = None,
    top_k_per_topic: int = 1,
) -> list[FilingEvidence]:
    index = build_index_from_text(ticker, text, Path(source_url))
    return _retrieve_from_index(
        ticker=ticker,
        company_name=company_name,
        index=index,
        topics=topics,
        top_k_per_topic=top_k_per_topic,
        source_title=source_title,
        source_url=source_url,
        source_date=source_date,
    )


def _retrieve_from_index(
    ticker: str,
    company_name: str,
    index: SimpleVectorIndex,
    topics: list[str],
    top_k_per_topic: int,
    source_title: str,
    source_url: str | None,
    source_date: str | None,
) -> list[FilingEvidence]:
    evidence: list[FilingEvidence] = []
    seen_chunks: set[str] = set()
    for topic in topics:
        for chunk, score in index.search(topic, top_k=top_k_per_topic):
            if chunk.id in seen_chunks:
                continue
            seen_chunks.add(chunk.id)
            citation = Citation(
                id=f"filing-{chunk.id}",
                source="SEC EDGAR" if source_url and source_url.startswith("https://www.sec.gov") else "CapitalLens Sample Filing Corpus",
                title=source_title,
                url=source_url or str(chunk.source_path),
                date=source_date,
                snippet=chunk.text[:350],
            )
            evidence.append(
                FilingEvidence(
                    topic=topic,
                    claim=_summarize_chunk(topic, chunk.text),
                    citation=citation,
                    relevance_score=round(score, 3),
                )
            )
    return evidence


def _summarize_chunk(topic: str, text: str) -> str:
    first_sentence = text.split(".")[0].strip()
    if not first_sentence:
        return f"Filing evidence related to {topic}."
    return first_sentence + "."
