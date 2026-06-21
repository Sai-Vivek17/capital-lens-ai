"""Persistent SQLite storage for the Phase 2 hybrid RAG index."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class RAGIndexStore:
    """Small persistent vector/lexical chunk store.

    It is intentionally dependency-light for local reliability, but the schema
    mirrors a production vector store: documents, chunks, embeddings, metadata,
    and content hashes are persisted separately.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_documents (
                    document_id TEXT PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT,
                    date TEXT,
                    content_hash TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    text TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    token_json TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES rag_documents(document_id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_documents_ticker ON rag_documents(ticker)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_ticker ON rag_chunks(ticker)")

    def upsert_document(
        self,
        document_id: str,
        ticker: str,
        source: str,
        title: str,
        url: str | None,
        date: str | None,
        content_hash: str,
        metadata: dict[str, Any],
        text: str,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO rag_documents (document_id, ticker, source, title, url, date, content_hash, metadata_json, text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    ticker=excluded.ticker,
                    source=excluded.source,
                    title=excluded.title,
                    url=excluded.url,
                    date=excluded.date,
                    content_hash=excluded.content_hash,
                    metadata_json=excluded.metadata_json,
                    text=excluded.text
                """,
                (document_id, ticker, source, title, url, date, content_hash, json.dumps(metadata, sort_keys=True), text),
            )

    def replace_chunks(self, document_id: str, chunks: list[dict[str, Any]]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM rag_chunks WHERE document_id = ?", (document_id,))
            conn.executemany(
                """
                INSERT INTO rag_chunks (chunk_id, document_id, ticker, ordinal, text, token_json, embedding_json, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk["chunk_id"],
                        document_id,
                        chunk["ticker"],
                        chunk["ordinal"],
                        chunk["text"],
                        json.dumps(chunk["tokens"]),
                        json.dumps(chunk["embedding"]),
                        json.dumps(chunk.get("metadata", {}), sort_keys=True),
                    )
                    for chunk in chunks
                ],
            )

    def document_hash(self, document_id: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute("SELECT content_hash FROM rag_documents WHERE document_id = ?", (document_id,)).fetchone()
        return row["content_hash"] if row else None

    def load_chunks(self, ticker: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT c.chunk_id, c.document_id, c.ticker, c.ordinal, c.text, c.token_json, c.embedding_json,
                   c.metadata_json, d.source, d.title, d.url, d.date
            FROM rag_chunks c
            JOIN rag_documents d ON d.document_id = c.document_id
        """
        params: tuple[str, ...] = ()
        if ticker:
            query += " WHERE c.ticker = ?"
            params = (ticker,)
        query += " ORDER BY c.document_id, c.ordinal"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "ticker": row["ticker"],
                "ordinal": row["ordinal"],
                "text": row["text"],
                "tokens": json.loads(row["token_json"]),
                "embedding": json.loads(row["embedding_json"]),
                "metadata": json.loads(row["metadata_json"]),
                "source": row["source"],
                "title": row["title"],
                "url": row["url"],
                "date": row["date"],
            }
            for row in rows
        ]

    def stats(self, ticker: str | None = None) -> tuple[int, int]:
        with self.connect() as conn:
            if ticker:
                docs = conn.execute("SELECT COUNT(*) AS count FROM rag_documents WHERE ticker = ?", (ticker,)).fetchone()["count"]
                chunks = conn.execute("SELECT COUNT(*) AS count FROM rag_chunks WHERE ticker = ?", (ticker,)).fetchone()["count"]
            else:
                docs = conn.execute("SELECT COUNT(*) AS count FROM rag_documents").fetchone()["count"]
                chunks = conn.execute("SELECT COUNT(*) AS count FROM rag_chunks").fetchone()["count"]
        return int(docs), int(chunks)

