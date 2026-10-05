import os, json, re
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from pydantic import SecretStr

load_dotenv()

groq_api_key = os.getenv("GROQ_ORCHESTRATOR_API_KEY", os.getenv("GROQ_API_KEY"))

llm = ChatGroq(model="openai/gpt-oss-20b", api_key=SecretStr(groq_api_key) if groq_api_key else None)


def extract_json(text: str) -> str:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response: {text}")
    return match.group(0)


def response_content_to_text(content: str | list[str | dict]) -> str:
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


def find_disagreements_llm(agent_outputs: list[dict]) -> list[tuple[dict, dict]]:
    claims_summary = "\n".join(
        f"{o['agent']}: {o['key_claim']} (score: {o['score']})" for o in agent_outputs
    )

    prompt = f"""Here are 4 independent analysts' conclusions about a company:
{claims_summary}

Identify pairs of analysts whose conclusions are in GENUINE tension or contradiction 
(not just different topics — actual disagreement about whether this is a good investment).
Respond with ONLY valid JSON, no other text: {{"disagreements": [["agent1", "agent2"]]}}
If no real tension exists, return {{"disagreements": []}}
"""

    response = llm.invoke(prompt)
    raw = response_content_to_text(response.content)

    json_str = extract_json(raw)
    result = json.loads(json_str)

    pairs = []
    for name1, name2 in result["disagreements"]:
        a = next(o for o in agent_outputs if o["agent"] == name1)
        b = next(o for o in agent_outputs if o["agent"] == name2)
        pairs.append((a, b))
    return pairs

def run_debate_turn(agent_output: dict, opponent_output: dict) -> dict:
    """One agent responds to another's conflicting claim: defend, revise, or concede."""

    prompt = f"""You previously concluded: "{agent_output['key_claim']}" (score: {agent_output['score']})
Your own noted weak point was: "{agent_output['contrarian_point']}"

Another independent analyst concluded the opposite: "{opponent_output['key_claim']}" (score: {opponent_output['score']})

Respond with exactly one of: DEFEND, REVISE, or UNRESOLVED.
- DEFEND: restate your position with added reasoning for why their point doesn't change it
- REVISE: update your score/claim in light of their evidence
- UNRESOLVED: acknowledge this disagreement is legitimate and can't be settled with current information

Respond with ONLY valid JSON, no other text:
{{"verdict": "defend|revise|unresolved", "updated_score": <1-5 integer>, "reasoning": "<1-2 sentences>"}}
"""
    response = llm.invoke(prompt)
    raw = response_content_to_text(response.content)
    json_str = extract_json(raw)
    result = json.loads(json_str)
    result["agent"] = agent_output["agent"]
    return result