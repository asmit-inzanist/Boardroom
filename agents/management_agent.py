# agents/management_agent.py

from agents.base_agent import run_agent

PERSONA = """You are a governance-focused analyst evaluating company leadership.
Assess: does leadership appear trustworthy and competent based on the filing excerpt and company data provided? 
Are there any governance red flags (unusual compensation structures, concentrated control, related-party 
concerns)? Be specific — reference actual details from the filing excerpt, not general assumptions about 
corporate governance."""


def run_management_agent(data_bundle: dict):
    trimmed_data = {
        "ticker": data_bundle["ticker"],
        "filing_excerpt": data_bundle.get("filing_excerpt", "")[:3000],  # cap length
    }

    return run_agent(
        PERSONA,
        trimmed_data,
        agent_name="management_governance"
    )