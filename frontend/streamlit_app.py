"""Streamlit frontend for CapitalLens AI."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.main import CapitalLensOrchestrator
from app.schemas.models import AgentStep, ResearchRequest, ResearchResult
from app.storage.database import add_watchlist_ticker, list_recent_alerts, list_watchlist, remove_watchlist_ticker
from app.tools.export_tools import markdown_to_pdf_bytes, save_markdown_report
from app.tools.finance_tools import format_money


st.set_page_config(page_title="CapitalLens AI", page_icon="CL", layout="wide", initial_sidebar_state="expanded")


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --cl-bg: #0f172a;
            --cl-panel: #111827;
            --cl-accent: #14b8a6;
            --cl-accent-2: #f59e0b;
            --cl-text: #e5e7eb;
        }
        .main .block-container {
            padding-top: 2rem;
            max-width: 1320px;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #111827 58%, #171717 100%);
        }
        [data-testid="stSidebar"] * {
            color: #f8fafc;
        }
        .cl-hero {
            padding: 24px 28px;
            border: 1px solid rgba(20,184,166,.28);
            background:
                linear-gradient(135deg, rgba(20,184,166,.18), rgba(245,158,11,.10)),
                #0f172a;
            border-radius: 8px;
            margin-bottom: 18px;
        }
        .cl-hero h1 {
            margin: 0 0 6px 0;
            color: #f8fafc;
            font-size: 2.2rem;
            letter-spacing: 0;
        }
        .cl-hero p {
            margin: 0;
            color: #cbd5e1;
            font-size: 1rem;
            line-height: 1.5;
        }
        .metric-card {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 14px 16px;
            background: #ffffff;
            min-height: 104px;
            box-shadow: 0 1px 2px rgba(15,23,42,.06);
        }
        .metric-card .label {
            font-size: .78rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0;
            margin-bottom: 7px;
        }
        .metric-card .value {
            color: #0f172a;
            font-weight: 750;
            font-size: 1.45rem;
            line-height: 1.15;
            overflow-wrap: anywhere;
        }
        .metric-card .caption {
            color: #64748b;
            margin-top: 5px;
            font-size: .82rem;
        }
        .step-row {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            padding: 9px 0;
            border-bottom: 1px solid #e5e7eb;
        }
        .step-dot {
            width: 11px;
            height: 11px;
            border-radius: 50%;
            margin-top: 6px;
            background: #14b8a6;
            flex: 0 0 11px;
        }
        .step-name {
            font-weight: 700;
            color: #0f172a;
        }
        .step-detail {
            color: #475569;
            font-size: .92rem;
        }
        .alert-high {
            border-left: 4px solid #dc2626;
            padding: 10px 12px;
            background: #fff1f2;
            border-radius: 6px;
            margin: 6px 0;
        }
        .alert-medium {
            border-left: 4px solid #f59e0b;
            padding: 10px 12px;
            background: #fffbeb;
            border-radius: 6px;
            margin: 6px 0;
        }
        .alert-low {
            border-left: 4px solid #14b8a6;
            padding: 10px 12px;
            background: #f0fdfa;
            border-radius: 6px;
            margin: 6px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, caption: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
            <div class="caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_steps(steps: list[AgentStep]) -> None:
    if not steps:
        st.info("Agent progress will appear here once the run starts.")
        return
    html = []
    for step in steps[-12:]:
        html.append(
            f"""
            <div class="step-row">
                <div class="step-dot"></div>
                <div>
                    <div class="step-name">{step.name} - {step.status}</div>
                    <div class="step-detail">{step.detail}</div>
                </div>
            </div>
            """
        )
    st.markdown("".join(html), unsafe_allow_html=True)


def research_page() -> None:
    st.markdown(
        """
        <div class="cl-hero">
            <h1>CapitalLens AI</h1>
            <p>Autonomous financial research and productivity agent for fast, cited public-company memos.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Research Console")
        query = st.text_input("Ticker or company", value="AAPL", placeholder="AAPL, MSFT, RELIANCE.NS, TCS.NS, Tesla")
        mode = st.selectbox("Research depth", ["Quick Scan", "Full Analyst Memo", "Risk-First Review"], index=1)
        settings = get_settings()
        demo_mode = st.toggle("Demo mode", value=settings.demo_mode)
        run_clicked = st.button("Run Agent", type="primary", use_container_width=True)
        st.divider()
        st.caption("Demo corpus includes Apple, Microsoft, Tesla, Reliance, and TCS.")

    if "last_result" not in st.session_state:
        st.session_state.last_result = None

    progress_box = st.container()
    if run_clicked:
        progress_steps: list[AgentStep] = []
        placeholder = progress_box.empty()

        def on_progress(step: AgentStep) -> None:
            progress_steps.append(step)
            with placeholder.container():
                st.subheader("Agent Progress")
                render_steps(progress_steps)

        try:
            orchestrator = CapitalLensOrchestrator()
            with st.spinner("CapitalLens agents are working..."):
                result = orchestrator.run_research(ResearchRequest(query=query, mode=mode, demo_mode=demo_mode), progress_callback=on_progress)
            st.session_state.last_result = result
            st.success(f"Research memo generated for {result.report.company_name}.")
        except Exception as exc:
            st.error(f"Research run failed: {exc}")

    result: ResearchResult | None = st.session_state.last_result
    if result is None:
        st.info("Start with a ticker or company name in the sidebar.")
        return

    bundle = result.bundle
    market = bundle.market_data
    metrics = market.metrics

    cols = st.columns(5)
    with cols[0]:
        metric_card("Price", f"{metrics.currency} {metrics.price:,.2f}" if metrics.price else "Unavailable", market.ticker)
    with cols[1]:
        metric_card("Market Cap", format_money(metrics.market_cap, metrics.currency), market.exchange or "Exchange unavailable")
    with cols[2]:
        metric_card("Financial Health", f"{bundle.scores.financial_health}/100", bundle.scores.confidence + " confidence")
    with cols[3]:
        metric_card("Risk Score", f"{bundle.scores.risk}/100", bundle.risks.summary.split(";")[0])
    with cols[4]:
        metric_card("Momentum", f"{bundle.scores.momentum}/100", bundle.news.overall_tone.title() + " news tone")

    with st.expander("Agent Plan", expanded=False):
        plan_df = pd.DataFrame([{"Agent": task.agent, "Objective": task.objective, "Tools": ", ".join(task.tools)} for task in bundle.plan.tasks])
        st.dataframe(plan_df, use_container_width=True, hide_index=True)

    tab_overview, tab_financials, tab_news, tab_risks, tab_valuation, tab_memo = st.tabs(
        ["Overview", "Financials", "News", "Risks", "Valuation", "Final Memo"]
    )

    with tab_overview:
        left, right = st.columns([1.25, 1])
        with left:
            st.subheader(market.company_name)
            st.write(market.description)
            st.write(f"**Sector:** {market.sector or 'Unavailable'}")
            st.write(f"**Industry:** {market.industry or 'Unavailable'}")
            st.write(f"**Data source:** {market.source}")
        with right:
            price_df = pd.DataFrame([point.dict() for point in market.price_history])
            if not price_df.empty:
                price_df["date"] = pd.to_datetime(price_df["date"])
                st.line_chart(price_df.set_index("date")["close"], height=280)

    with tab_financials:
        cols = st.columns(3)
        with cols[0]:
            st.metric("Revenue TTM", format_money(metrics.revenue_ttm, metrics.currency))
            st.metric("Revenue Growth", f"{metrics.revenue_growth * 100:.1f}%" if metrics.revenue_growth is not None else "Unavailable")
        with cols[1]:
            st.metric("Net Income TTM", format_money(metrics.net_income_ttm, metrics.currency))
            st.metric("Profit Growth", f"{metrics.profit_growth * 100:.1f}%" if metrics.profit_growth is not None else "Unavailable")
        with cols[2]:
            st.metric("Free Cash Flow", format_money(metrics.free_cash_flow_ttm, metrics.currency))
            st.metric("Debt / Equity", f"{metrics.debt_to_equity:.2f}" if metrics.debt_to_equity is not None else "Unavailable")

        trend_df = pd.DataFrame([point.dict() for point in market.financial_trends])
        if not trend_df.empty:
            st.subheader("Revenue and Profit Trend")
            chart_df = trend_df.set_index("period")[["revenue", "net_income"]]
            st.bar_chart(chart_df, height=320)

    with tab_news:
        for item in bundle.news.items:
            st.markdown(f"**{item.title}**")
            st.caption(f"{item.source} | {item.date} | Impact: {item.impact}")
            st.write(item.summary)
            st.divider()

    with tab_risks:
        risk_df = pd.DataFrame([risk.dict() for risk in bundle.risks.risks])
        st.dataframe(risk_df[["category", "severity", "description", "evidence", "citation_id"]], use_container_width=True, hide_index=True)
        severity_counts = risk_df.groupby("severity").size().reset_index(name="count") if not risk_df.empty else pd.DataFrame()
        if not severity_counts.empty:
            st.subheader("Risk Severity Distribution")
            st.bar_chart(severity_counts.set_index("severity")["count"], height=240)

    with tab_valuation:
        valuation_df = pd.DataFrame([metric.dict() for metric in bundle.valuation.metrics])
        st.dataframe(valuation_df, use_container_width=True, hide_index=True)
        peer_df = pd.DataFrame([peer.dict() for peer in bundle.valuation.peers])
        if not peer_df.empty:
            st.subheader("Peer Snapshot")
            st.dataframe(peer_df, use_container_width=True, hide_index=True)
        st.info(bundle.valuation.summary)

    with tab_memo:
        st.markdown(result.report.markdown)
        saved_path = save_markdown_report(result.report.markdown, result.report.ticker)
        st.caption(f"Latest markdown saved to {saved_path}")
        md_bytes = result.report.markdown.encode("utf-8")
        pdf_bytes = markdown_to_pdf_bytes(result.report.markdown)
        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button("Download Markdown", data=md_bytes, file_name=f"{result.report.ticker}-capital-lens-memo.md", mime="text/markdown", use_container_width=True)
        with col_b:
            st.download_button("Download PDF", data=pdf_bytes, file_name=f"{result.report.ticker}-capital-lens-memo.pdf", mime="application/pdf", use_container_width=True)


def watchlist_page() -> None:
    st.markdown(
        """
        <div class="cl-hero">
            <h1>Watchlist Monitor</h1>
            <p>Scan tracked companies for price movement, negative events, volatility, weak trends, and risk-score changes.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    orchestrator = CapitalLensOrchestrator()

    with st.sidebar:
        st.header("Watchlist")
        ticker = st.text_input("Add ticker", value="TSLA")
        add_col, remove_col = st.columns(2)
        with add_col:
            if st.button("Add", use_container_width=True):
                try:
                    add_watchlist_ticker(ticker)
                    st.success(f"Added {ticker}.")
                except Exception as exc:
                    st.error(str(exc))
        with remove_col:
            if st.button("Remove", use_container_width=True):
                try:
                    remove_watchlist_ticker(ticker)
                    st.success(f"Removed {ticker}.")
                except Exception as exc:
                    st.error(str(exc))
        scan_clicked = st.button("Scan Watchlist", type="primary", use_container_width=True)

    items = list_watchlist()
    if not items:
        st.info("Add AAPL, MSFT, TSLA, RELIANCE.NS, or TCS.NS to start monitoring.")
        return

    st.subheader("Tracked Companies")
    st.dataframe(pd.DataFrame([item.dict() for item in items]), use_container_width=True, hide_index=True)

    if scan_clicked:
        progress_steps: list[AgentStep] = []
        placeholder = st.empty()

        def on_progress(step: AgentStep) -> None:
            progress_steps.append(step)
            with placeholder.container():
                render_steps(progress_steps)

        with st.spinner("Scanning watchlist..."):
            scans = orchestrator.scan_watchlist(progress_callback=on_progress)
        st.session_state.last_scans = scans
        st.success(f"Scanned {len(scans)} companies.")

    scans = st.session_state.get("last_scans", [])
    if scans:
        rows = []
        for scan in scans:
            rows.append(
                {
                    "Ticker": scan.ticker,
                    "Price Change %": round(scan.price_change_pct or 0, 2),
                    "Risk Score": scan.risk_score,
                    "Momentum": scan.momentum_score,
                    "Alerts": len(scan.alerts),
                }
            )
        st.subheader("Latest Scan")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        for scan in scans:
            for alert in scan.alerts:
                st.markdown(
                    f"<div class='alert-{alert.severity}'><b>{alert.ticker} - {alert.category}</b><br>{alert.message}</div>",
                    unsafe_allow_html=True,
                )

    recent_alerts = list_recent_alerts(limit=10)
    if recent_alerts:
        st.subheader("Recent Stored Alerts")
        st.dataframe(pd.DataFrame([alert.dict() for alert in recent_alerts]), use_container_width=True, hide_index=True)


def main() -> None:
    inject_css()
    with st.sidebar:
        page = st.radio("Workspace", ["Research Agent", "Watchlist Monitor"], label_visibility="collapsed")
    if page == "Research Agent":
        research_page()
    else:
        watchlist_page()


if __name__ == "__main__":
    main()

