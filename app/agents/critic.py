"""CriticAgent reviews final memo for safety and support quality."""

from __future__ import annotations

import re

from app.schemas.models import ReportOutput, ResearchBundle
from app.tools.citation_audit import audit_rag_diagnostics, missing_citations


class CriticAgent:
    name = "CriticAgent"

    DIRECT_ADVICE_RE = re.compile(
        r"\b(strong buy|buy now|sell now|short now|dump|load up on|go long|go short)\b",
        re.IGNORECASE,
    )

    def run(self, report: ReportOutput, bundle: ResearchBundle) -> ReportOutput:
        notes: list[str] = []
        markdown = report.markdown

        if self.DIRECT_ADVICE_RE.search(markdown):
            markdown = self.DIRECT_ADVICE_RE.sub("review", markdown)
            notes.append("Replaced direct trading language with research-oriented wording.")

        missing = missing_citations(markdown, report.citations)
        if missing:
            notes.append(f"Found citation placeholders not present in source list: {', '.join(missing[:5])}.")

        rag_notes = audit_rag_diagnostics(bundle.filing_rag.diagnostics)
        notes.extend(rag_notes)
        if rag_notes and "## 9. Agent Conclusion" in markdown:
            source_note = (
                "\n\n**Source fidelity note:** "
                + " ".join(rag_notes)
                + "\n"
            )
            markdown = markdown.replace("## 9. Agent Conclusion", source_note + "\n## 9. Agent Conclusion")

        if "Disclaimer" not in markdown:
            markdown += "\n\n## Disclaimer\nCapitalLens AI is for research and educational purposes only and is not investment advice.\n"
            notes.append("Added missing safety disclaimer.")

        if bundle.scores.confidence == "Low":
            insert = "\n\n**Source quality note:** Overall confidence is Low because some data fields or source coverage are limited. Treat conclusions as preliminary.\n"
            markdown = markdown.replace("## 9. Agent Conclusion", insert + "\n## 9. Agent Conclusion")
            notes.append("Added low-confidence source quality note.")

        report.markdown = markdown
        report.critic_notes = notes or ["No critical citation or safety issues detected in deterministic review."]
        return report
