"""PlannerAgent builds an explicit research plan for each request."""

from __future__ import annotations

from app.schemas.models import PlanTask, ResearchPlan, ResearchRequest


class PlannerAgent:
    name = "PlannerAgent"

    def run(self, request: ResearchRequest) -> ResearchPlan:
        base_tasks = [
            PlanTask(
                agent="MarketDataAgent",
                objective="Resolve ticker and collect market price, core ratios, historical prices, and available financial trends.",
                tools=["yfinance", "CapitalLens demo dataset"],
                expected_output="Structured MarketData JSON with citations.",
            ),
            PlanTask(
                agent="NewsAgent",
                objective="Collect recent business events and classify each item as positive, neutral, or negative.",
                tools=["NEWS_API_KEY provider", "demo news fallback"],
                expected_output="Relevant news summary with event-level citations.",
            ),
            PlanTask(
                agent="FilingRAGAgent",
                objective="Retrieve evidence from filings for business model, competition, debt, regulation, and management commentary.",
                tools=["ChromaDB-compatible retriever", "sample filing corpus"],
                expected_output="Evidence snippets with citation IDs.",
            ),
            PlanTask(
                agent="RiskAgent",
                objective="Score financial, business, valuation, market, regulatory, and execution risks.",
                tools=["risk scoring rules", "market/news/RAG evidence"],
                expected_output="Risk matrix with 1-5 severity ratings and an aggregate risk score.",
            ),
            PlanTask(
                agent="ValuationAgent",
                objective="Build a simple valuation snapshot using available P/E, P/S, EV/EBITDA, and peer context.",
                tools=["market data", "peer comparison dataset"],
                expected_output="Valuation metrics and peer comparison with unavailable fields called out.",
            ),
            PlanTask(
                agent="ReportAgent",
                objective="Write a concise analyst-style memo with citations, scores, bull case, bear case, and safety disclaimer.",
                tools=["structured agent outputs", "optional OpenAI-compatible LLM polish"],
                expected_output="Professional markdown research memo.",
            ),
            PlanTask(
                agent="CriticAgent",
                objective="Review the memo for unsupported claims, missing citations, hallucination risk, and direct advice language.",
                tools=["citation checker", "safety language rules"],
                expected_output="Improved final report and critic notes.",
            ),
        ]

        if request.mode == "Quick Scan":
            tasks = [task for task in base_tasks if task.agent in {"MarketDataAgent", "NewsAgent", "FilingRAGAgent", "RiskAgent", "ValuationAgent", "ReportAgent", "CriticAgent"}]
        elif request.mode == "Risk-First Review":
            tasks = [base_tasks[0], base_tasks[1], base_tasks[2], base_tasks[3], base_tasks[4], base_tasks[5], base_tasks[6]]
            tasks[0].objective += " Prioritize downside indicators before upside narrative."
            tasks[3].objective = "Lead with downside detection across financial, market, regulatory, concentration, valuation, and execution risks."
        else:
            tasks = base_tasks

        return ResearchPlan(
            query=request.query,
            mode=request.mode,
            tasks=tasks,
            success_criteria=[
                "Every major claim is grounded in market data, news, or retrieved filing evidence where possible.",
                "Unavailable ratios or filings are explicitly labeled instead of invented.",
                "Conclusion is research-oriented and avoids direct buy/sell instructions.",
                "Report is exportable as Markdown and PDF.",
            ],
        )
