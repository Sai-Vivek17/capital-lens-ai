"""Advanced local RAG framework with persistent hybrid retrieval.

Phase 2 goals:
- persistent document/chunk index
- deterministic local embeddings for demo-safe execution
- BM25-style lexical score + vector similarity + reranking
- retrieval diagnostics and citation-support auditing
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.schemas.models import Citation, FilingEvidence, RAGDiagnostics, RetrievalHit
from app.storage.rag_store import RAGIndexStore
from app.tools.rag_tools import chunk_text

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9\-]{2,}")
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "are",
    "can",
    "into",
    "its",
    "has",
    "have",
    "may",
    "will",
    "company",
    "business",
}


@dataclass(frozen=True)
class RAGDocument:
    ticker: str
    source: str
    title: str
    text: str
    url: str | None = None
    date: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def document_id(self) -> str:
        payload = f"{self.ticker}|{self.source}|{self.title}|{self.url or ''}"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:18]
        return f"{self.ticker}-{digest}"

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text) if token.lower() not in STOPWORDS]


def deterministic_embedding(text: str, dimensions: int = 384) -> list[float]:
    """Generate a stable local embedding without external APIs.

    Each token maps to two signed hashed dimensions. This is not a replacement
    for a domain embedding model, but it gives reliable vector behavior in
    offline demos and tests while preserving the vector-store architecture.
    """

    vector = [0.0] * dimensions
    counts = Counter(tokenize(text))
    if not counts:
        return vector
    for token, count in counts.items():
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        for offset in (0, 8):
            idx = int.from_bytes(digest[offset : offset + 4], "big") % dimensions
            sign = 1.0 if digest[offset + 4] % 2 == 0 else -1.0
            vector[idx] += sign * (1.0 + math.log(count))
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


class HybridRAGIndex:
    """Persistent hybrid search index with deterministic local embeddings."""

    def __init__(self, store: RAGIndexStore, dimensions: int = 384) -> None:
        self.store = store
        self.dimensions = dimensions

    def ingest(self, documents: list[RAGDocument], max_words: int = 90) -> None:
        for document in documents:
            if self.store.document_hash(document.document_id) == document.content_hash:
                continue
            chunks = []
            for ordinal, chunk in enumerate(chunk_text(document.text, max_words=max_words), start=1):
                metadata = {**document.metadata, "ticker": document.ticker, "ordinal": ordinal}
                chunks.append(
                    {
                        "chunk_id": f"{document.document_id}-chunk-{ordinal}",
                        "ticker": document.ticker,
                        "ordinal": ordinal,
                        "text": chunk,
                        "tokens": tokenize(chunk),
                        "embedding": deterministic_embedding(chunk, dimensions=self.dimensions),
                        "metadata": metadata,
                    }
                )
            self.store.upsert_document(
                document_id=document.document_id,
                ticker=document.ticker,
                source=document.source,
                title=document.title,
                url=document.url,
                date=document.date,
                content_hash=document.content_hash,
                metadata=document.metadata,
                text=document.text,
            )
            self.store.replace_chunks(document.document_id, chunks)

    def retrieve(self, query: str, ticker: str | None = None, top_k: int = 5) -> list[RetrievalHit]:
        chunks = self.store.load_chunks(ticker=ticker)
        if not chunks:
            return []
        query_tokens = tokenize(query)
        query_counts = Counter(query_tokens)
        query_embedding = deterministic_embedding(query, dimensions=self.dimensions)
        doc_freq = Counter()
        for chunk in chunks:
            doc_freq.update(set(chunk["tokens"]))

        scored: list[RetrievalHit] = []
        lexical_raw: list[float] = []
        vector_raw: list[float] = []
        for chunk in chunks:
            token_counts = Counter(chunk["tokens"])
            lexical = self._bm25(query_counts, token_counts, doc_freq, total_docs=len(chunks))
            vector = max(0.0, cosine_similarity(query_embedding, chunk["embedding"]))
            lexical_raw.append(lexical)
            vector_raw.append(vector)
            scored.append(
                RetrievalHit(
                    chunk_id=chunk["chunk_id"],
                    document_id=chunk["document_id"],
                    text=chunk["text"],
                    source=chunk["source"],
                    title=chunk["title"],
                    url=chunk["url"],
                    date=chunk["date"],
                    metadata=chunk["metadata"],
                    lexical_score=lexical,
                    vector_score=vector,
                )
            )

        max_lexical = max(lexical_raw) or 1.0
        max_vector = max(vector_raw) or 1.0
        for hit in scored:
            overlap = self._overlap_bonus(query_tokens, tokenize(hit.text))
            topic_bonus = 0.08 if ticker and hit.metadata.get("ticker") == ticker else 0.0
            hit.lexical_score = round(hit.lexical_score / max_lexical, 4)
            hit.vector_score = round(hit.vector_score / max_vector, 4)
            hit.rerank_score = round(min(1.0, overlap + topic_bonus), 4)
            hit.final_score = round(0.48 * hit.lexical_score + 0.34 * hit.vector_score + 0.18 * hit.rerank_score, 4)

        scored.sort(key=lambda item: item.final_score, reverse=True)
        return [hit for hit in scored[:top_k] if hit.final_score > 0.05]

    @staticmethod
    def _bm25(query: Counter[str], doc: Counter[str], doc_freq: Counter[str], total_docs: int) -> float:
        if not query or not doc:
            return 0.0
        k1 = 1.5
        b = 0.75
        avg_len = 80
        doc_len = max(sum(doc.values()), 1)
        score = 0.0
        for term, q_count in query.items():
            freq = doc.get(term, 0)
            if freq == 0:
                continue
            idf = math.log(1 + (total_docs - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            numerator = freq * (k1 + 1)
            denominator = freq + k1 * (1 - b + b * doc_len / avg_len)
            score += q_count * idf * numerator / denominator
        return score

    @staticmethod
    def _overlap_bonus(query_tokens: list[str], doc_tokens: list[str]) -> float:
        if not query_tokens:
            return 0.0
        overlap = len(set(query_tokens) & set(doc_tokens)) / max(len(set(query_tokens)), 1)
        phrase_bonus = 0.12 if " ".join(query_tokens[:2]) in " ".join(doc_tokens) else 0.0
        return min(1.0, overlap + phrase_bonus)


class RAGPipeline:
    """High-level RAG pipeline used by FilingRAGAgent."""

    def __init__(self, store: RAGIndexStore, dimensions: int = 384) -> None:
        self.index = HybridRAGIndex(store=store, dimensions=dimensions)
        self.store = store

    def ingest_and_retrieve(
        self,
        documents: list[RAGDocument],
        topics: list[str],
        top_k_per_topic: int = 1,
    ) -> tuple[list[FilingEvidence], RAGDiagnostics]:
        self.index.ingest(documents)
        evidence: list[FilingEvidence] = []
        top_scores: list[float] = []
        seen_pairs: set[tuple[str, str]] = set()
        ticker = documents[0].ticker if documents else None
        for topic in topics:
            for hit in self.index.retrieve(topic, ticker=ticker, top_k=top_k_per_topic + 2):
                evidence_key = (topic, hit.chunk_id)
                if evidence_key in seen_pairs:
                    continue
                seen_pairs.add(evidence_key)
                top_scores.append(hit.final_score)
                citation = Citation(
                    id=f"filing-{hit.chunk_id}",
                    source=hit.source,
                    title=hit.title,
                    url=hit.url,
                    date=hit.date,
                    snippet=hit.text[:350],
                )
                evidence.append(
                    FilingEvidence(
                        topic=topic,
                        claim=summarize_evidence(topic, hit.text),
                        citation=citation,
                        relevance_score=hit.final_score,
                        retrieval_scores={
                            "lexical": hit.lexical_score,
                            "vector": hit.vector_score,
                            "rerank": hit.rerank_score,
                            "final": hit.final_score,
                        },
                    )
                )
                break
        docs_count, chunks_count = self.store.stats(ticker=ticker)
        diagnostics = build_diagnostics(
            topics=topics,
            evidence=evidence,
            indexed_documents=docs_count,
            indexed_chunks=chunks_count,
            top_scores=top_scores,
        )
        return evidence, diagnostics


def build_diagnostics(
    topics: list[str],
    evidence: list[FilingEvidence],
    indexed_documents: int,
    indexed_chunks: int,
    top_scores: list[float],
) -> RAGDiagnostics:
    covered_topics = {item.topic for item in evidence}
    citation_coverage = len(covered_topics) / max(len(topics), 1)
    avg_score = sum(top_scores) / len(top_scores) if top_scores else 0.0
    unsupported = [topic for topic in topics if topic not in covered_topics]
    if citation_coverage >= 0.85 and avg_score >= 0.45:
        coverage = "High"
    elif citation_coverage >= 0.5:
        coverage = "Medium"
    else:
        coverage = "Low"
    return RAGDiagnostics(
        retrieval_strategy="hybrid_bm25_hash_embedding_rerank",
        indexed_documents=indexed_documents,
        indexed_chunks=indexed_chunks,
        queries=topics,
        average_top_score=round(avg_score, 4),
        coverage=coverage,
        citation_coverage=round(citation_coverage, 4),
        unsupported_claims=unsupported,
    )


def summarize_evidence(topic: str, text: str) -> str:
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]
    if not sentences:
        return f"Retrieved evidence related to {topic}."
    topic_terms = set(tokenize(topic))
    best = max(sentences, key=lambda sentence: len(topic_terms & set(tokenize(sentence))))
    return best if best.endswith((".", "!", "?")) else best + "."
