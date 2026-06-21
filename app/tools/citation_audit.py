"""Citation and source-fidelity checks for generated research memos."""

from __future__ import annotations

import re

from app.schemas.models import Citation, RAGDiagnostics

CITATION_RE = re.compile(r"\[([A-Za-z0-9_.\-]+)\]")


def referenced_citation_ids(markdown: str) -> set[str]:
    return set(CITATION_RE.findall(markdown))


def missing_citations(markdown: str, citations: list[Citation]) -> list[str]:
    known = {citation.id for citation in citations}
    return sorted(ref_id for ref_id in referenced_citation_ids(markdown) if ref_id not in known and not ref_id.startswith("market-data"))


def audit_rag_diagnostics(diagnostics: RAGDiagnostics | None) -> list[str]:
    if diagnostics is None:
        return ["RAG diagnostics were unavailable for this run."]
    notes: list[str] = []
    if diagnostics.coverage == "Low":
        notes.append("RAG coverage is Low; retrieved evidence does not fully cover the requested research topics.")
    if diagnostics.citation_coverage < 0.75:
        notes.append(f"Citation coverage is {diagnostics.citation_coverage * 100:.0f}%, below the 75% review threshold.")
    if diagnostics.average_top_score < 0.25:
        notes.append("Average retrieval score is weak; memo claims should be treated as preliminary.")
    if diagnostics.unsupported_claims:
        notes.append("Unsupported retrieval topics: " + ", ".join(diagnostics.unsupported_claims[:5]) + ".")
    return notes

