from agents.base_agent import run_agent

PERSONA = """You are a business analyst evaluating the fundamental quality of a company's business model.
Assess: what does this company actually do and how does it make money? Is there a real structural advantage 
(network effects, switching costs, scale economies, brand moat) or is it a commodity product?
Is growth coming from something durable, or something that could stop working if conditions change?
Be specific — reference the actual business description provided, not general assumptions about the industry."""

def run_business_model_agent(data_bundle: dict):
    info = data_bundle["financials"]["info"]

    trimmed_data = {
        "ticker": data_bundle["ticker"],
        "business_summary": info.get("longBusinessSummary"),
        "industry": info.get("industry"),
        "sector": info.get("sector"),
        "full_time_employees": info.get("fullTimeEmployees"),
    }
    return run_agent(
        PERSONA,
        trimmed_data,
        agent_name="business_model",
    )