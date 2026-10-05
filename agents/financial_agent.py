# agents/financials_agent.py

from agents.base_agent import run_agent, PE_RATIO_TOOL

PERSONA = """You are a skeptical value-investing financial analyst.
Evaluate whether this company is fairly valued based on the data provided.
You have access to a pe_ratio tool — use it to calculate the exact P/E ratio rather than estimating or recalling one from memory or news text.
Consider P/E, revenue trends, margins, and cash flow. Be specific and critical."""


def run_financials_agent(data_bundle: dict):
    info = data_bundle["financials"]["info"]
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    eps = info.get("trailingEps")

    # Only send the relevant slice — not the full 250-row price history
    trimmed_data = {
        "ticker": data_bundle["ticker"],
        "financial_info": {
            k: info.get(k) for k in [
                "trailingPE", "forwardPE", "priceToBook", "marketCap",
                "trailingEps", "totalRevenue", "profitMargins",
                "operatingMargins", "freeCashflow", "debtToEquity"
            ]
        },
        "analysis_metrics": data_bundle.get("analysis_metrics", {}),
    }

    enriched_persona = f"""{PERSONA}

Known values for this company — use these exact numbers when calling pe_ratio, do not estimate or use any other figures:
- price: {price}
- eps: {eps}"""

    return run_agent(
        enriched_persona,
        trimmed_data,          # ← pass the trimmed dict, not the full bundle
        agent_name="financials_valuation",
        tools=[PE_RATIO_TOOL]
    )