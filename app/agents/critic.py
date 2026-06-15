"""CriticAgent reviews final memo for safety and support quality."""

from __future__ import annotations

import re

from app.schemas.models import ReportOutput, ResearchBundle


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

        citation_ids = {citation.id for citation in report.citations}
        referenced_ids = set(re.findall(r"\[([A-Za-z0-9_.\-]+)\]", markdown))
        missing = sorted(ref_id for ref_id in referenced_ids if ref_id not in citation_ids and not ref_id.startswith("market-data"))
        if missing:
            notes.append(f"Found citation placeholders not present in source list: {', '.join(missing[:5])}.")

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
