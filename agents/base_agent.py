import json
import os
import re
import threading
import time
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field, SecretStr
from typing import Literal
from tools.calculations import pe_ratio

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_REQUEST_DELAY_SECONDS = float(os.getenv("GROQ_REQUEST_DELAY_SECONDS", "10"))
_groq_request_lock = threading.Lock()
_last_groq_request_at = 0.0

llm = ChatGroq(
    model=GROQ_MODEL,
    api_key=(
        SecretStr(analyst_api_key)
        if (analyst_api_key := os.getenv("GROQ_ANALYST_API_KEY", os.getenv("GROQ_API_KEY")))
        else None
    ),
    temperature=0,
    timeout=60,
    max_retries=2,
)


class agentoutput(BaseModel):
    agent: str
    score: int = Field(ge=1, le=5)
    confidence: Literal["low", "medium", "high"]
    key_claim: str
    evidence: list[str]
    contrarian_point: str


PE_RATIO_TOOL = {
    'type': 'function',
    'function': {
        'name': 'pe_ratio',
        'description': 'Calculate the exact P/E ratio given a stock price and earnings-per-share.',
        'parameters': {
            'type': 'object',
            'properties': {
                'price': {'type': 'number'},
                'eps': {'type': 'number'}
            },
            'required': ['price', 'eps']
        }
    }
}

AVAILABLE_TOOLS = {
    "pe_ratio": pe_ratio
}


def _invoke_with_delay(model: Any, messages: list[Any]) -> Any:
    """Space analyst requests to avoid bursting through Groq's TPM limit."""
    global _last_groq_request_at

    with _groq_request_lock:
        elapsed = time.monotonic() - _last_groq_request_at
        delay = GROQ_REQUEST_DELAY_SECONDS - elapsed
        if delay > 0:
            time.sleep(delay)

        response = model.invoke(messages)
        _last_groq_request_at = time.monotonic()
        return response


def extract_json(text: str) -> str:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response: {text}")
    return match.group(0)


def response_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        ).strip()
    return str(content or "").strip()


def run_agent(persona_prompt: str, data_bundle: dict, agent_name: str, tools=None) -> agentoutput:
    tools = tools or []

    system_prompt = f"""{persona_prompt}

Company data:
{json.dumps(data_bundle, default=str)[:8000]}

Respond ONLY with valid JSON matching this exact shape, no other text:
{{
  "score": <1-5 integer>,
  "confidence": "<low|medium|high>",
  "key_claim": "<one sentence>",
  "evidence": ["<point 1>", "<point 2>"],
  "contrarian_point": "<strongest reason you could be wrong>"
}}
"""

    model = llm.bind_tools(tools) if tools else llm
    messages: list[Any] = [HumanMessage(content=system_prompt)]

    response = None
    raw_output = ""
    for attempt in range(3):
        response = _invoke_with_delay(model, messages)
        print(f"[{agent_name}] TOOL CALLS: {response.tool_calls or 'none'}")

        if response.tool_calls:
            messages.append(response)

            for call in response.tool_calls:
                fn_name = call["name"]
                fn_args = call["args"]

                if fn_name in AVAILABLE_TOOLS:
                    try:
                        result = AVAILABLE_TOOLS[fn_name](**fn_args)
                    except Exception as e:
                        result = f"Error running {fn_name}: {e}"
                else:
                    result = f"Unknown tool: {fn_name}"

                messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
            continue

        raw_output = response_content_to_text(response.content)
        if raw_output:
            break
        print(f"[{agent_name}] Empty response; retrying ({attempt + 1}/3)")
        messages.append(
            HumanMessage(
                content=(
                    "Your previous response was empty. Return the required JSON object now, "
                    "with no explanation or additional text."
                )
            )
        )

    if not raw_output:
        raise ValueError(f"Groq returned an empty response for {agent_name} after 3 attempts")

    json_str = extract_json(raw_output)
    parsed = json.loads(json_str)
    return agentoutput(agent=agent_name, **parsed)