# agents/risk_agent.py

from agents.base_agent import run_agent

PERSONA = """You are a skeptical risk analyst practicing inversion thinking: instead of asking what could go 
slightly wrong, ask specifically how this company could meaningfully fail or decline.
Assess: who is competing for the same customers, and is that pressure increasing? Are there any red-line 
issues (regulatory risk, key-person dependency, accounting concerns)? Be concrete — reference specific 
competitors or risks mentioned in the news/data provided, not generic industry risk."""


def run_risk_agent(data_bundle: dict):
    info = data_bundle["financials"]["info"]

    trimmed_data = {
        "ticker": data_bundle["ticker"],
        "industry": info.get("industry"),
        "sector": info.get("sector"),
        "news": data_bundle.get("news", [])[:5],  # cap to top 5, avoid flooding context
        "business_summary": info.get("longBusinessSummary"),
        "financial_risk_metrics": {
            "revenue_growth": data_bundle.get("analysis_metrics", {}).get("revenue_growth", {}),
            "earnings_growth": data_bundle.get("analysis_metrics", {}).get("earnings_growth", {}),
            "margins": data_bundle.get("analysis_metrics", {}).get("margins", {}),
            "debt": data_bundle.get("analysis_metrics", {}).get("debt", {}),
            "cash_flow": data_bundle.get("analysis_metrics", {}).get("cash_flow", {}),
        },
    }

    return run_agent(
        PERSONA,
        trimmed_data,
        agent_name="competitive_risk"
    )