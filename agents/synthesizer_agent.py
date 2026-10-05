# agents/synthesizer_agent.py

import os, json, re
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from pydantic import SecretStr

load_dotenv()

groq_api_key = os.getenv("GROQ_ORCHESTRATOR_API_KEY", os.getenv("GROQ_API_KEY"))

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=SecretStr(groq_api_key) if groq_api_key else None,
    timeout=60
)


def extract_json(text: str) -> str:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response: {text}")
    return match.group(0)


def response_content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    text_parts = []
    for block in content:
        if isinstance(block, str):
            text_parts.append(block)
        elif isinstance(block, dict):
            text = block.get("text")
            if isinstance(text, str):
                text_parts.append(text)
    return "".join(text_parts)


def synthesize_report(
    ticker: str,
    data_bundle: dict,
    agent_outputs: list[dict],
    disagreement_log: list[dict],
) -> dict:
    prompt = f"""You are the lead synthesizer for an investment research team analyzing {ticker}.

Agent outputs:
{json.dumps(agent_outputs, indent=2)}

Structured company metrics:
{json.dumps(data_bundle.get("analysis_metrics", {}), indent=2, default=str)}

Data metadata:
{json.dumps(data_bundle.get("metadata", {}), indent=2)}

Debate log:
{json.dumps(disagreement_log, indent=2)}

Produce a final report as JSON with this shape:
{{"ticker": "{ticker}", "composite_score": <1.0-5.0>, "verdict": "<Pass|Fail|Gray Zone>",
"one_line_conclusion": "<sentence>", "disagreement_summary": "<2-3 sentences>",
"financial_health": {{"revenue_growth": {{}}, "earnings_growth": {{}}, "margins": {{}},
"debt": {{}}, "cash_flow": {{}}}},
"valuation": {{}}, "analyst_consensus": {{}}, "target_price": {{}},
"risks": ["<evidence-based risk>"],
"scenarios": {{"bull": {{"case": "...", "conditions": ["..."]}},
"base": {{"case": "...", "conditions": ["..."]}},
"bear": {{"case": "...", "conditions": ["..."]}}}},
"data_quality": {{"fetched_at": "...", "sources": ["..."]}},
"recommendation": {{"aggressive": {{"action": "...", "price_range": "..."}},
"moderate": {{"action": "...", "price_range": "..."}},
"conservative": {{"action": "...", "price_range": "..."}}}}}}
Respond with ONLY the JSON, no other text."""

    response = llm.invoke(prompt)
    raw = response_content_to_text(response.content)
    json_str = extract_json(raw)
    report = json.loads(json_str)
    metrics = data_bundle.get("analysis_metrics", {})

    # Keep numeric/source sections grounded in fetched data even if the model
    # leaves one of the requested JSON sections out.
    report.setdefault("ticker", ticker)
    if not report.get("financial_health"):
        report["financial_health"] = {
        key: metrics.get(key, {})
        for key in ("revenue_growth", "earnings_growth", "margins", "debt", "cash_flow")
        }
    if not report.get("valuation"):
        report["valuation"] = metrics.get("valuation", {})
    if not report.get("analyst_consensus"):
        report["analyst_consensus"] = metrics.get("analyst_consensus", {})
    if not report.get("target_price"):
        report["target_price"] = metrics.get("target_price", {})
    report.setdefault("risks", [])
    report.setdefault("scenarios", {"bull": {}, "base": {}, "bear": {}})
    if not report.get("data_quality"):
        report["data_quality"] = data_bundle.get("metadata", {})
    return report