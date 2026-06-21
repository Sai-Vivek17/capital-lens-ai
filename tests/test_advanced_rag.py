from __future__ import annotations

from app.storage.rag_store import RAGIndexStore
from app.tools.advanced_rag import RAGDocument, RAGPipeline, deterministic_embedding


def test_deterministic_embedding_is_stable() -> None:
    left = deterministic_embedding("regulatory compliance platform risk", dimensions=64)
    right = deterministic_embedding("regulatory compliance platform risk", dimensions=64)
    other = deterministic_embedding("cash flow liquidity debt", dimensions=64)

    assert left == right
    assert left != other
    assert abs(sum(value * value for value in left) - 1.0) < 0.01


def test_hybrid_rag_retrieves_cited_evidence_with_diagnostics(tmp_path) -> None:
    store = RAGIndexStore(tmp_path / "rag_index.db")
    pipeline = RAGPipeline(store=store, dimensions=64)
    document = RAGDocument(
        ticker="DEMO",
        source="Unit Test Filing",
        title="Demo filing excerpt",
        text=(
            "The company faces regulatory compliance risk from platform access rules and privacy obligations.\n\n"
            "Revenue is generated from software subscriptions and professional services.\n\n"
            "Liquidity depends on operating cash flow, debt capacity, and disciplined capital spending."
        ),
        url="unit://filing",
        date="2026-06-21",
    )

    evidence, diagnostics = pipeline.ingest_and_retrieve(
        [document],
        topics=["regulatory compliance risk", "cash flow debt liquidity"],
        top_k_per_topic=1,
    )

    assert len(evidence) == 2
    assert diagnostics.indexed_documents == 1
    assert diagnostics.indexed_chunks >= 2
    assert diagnostics.citation_coverage == 1.0
    assert diagnostics.coverage in {"Medium", "High"}
    assert all(item.retrieval_scores["final"] > 0 for item in evidence)
