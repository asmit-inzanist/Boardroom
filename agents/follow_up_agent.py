import json
import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def answer_follow_up(report: dict, question: str, history: list[dict] | None = None) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    model = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        google_api_key=api_key,
        temperature=0.2,
        timeout=30,
    )
    prompt = f"""You are Boardroom's research report assistant.
Answer the user's question using only the generated report below.
If the report does not contain enough information, say so clearly instead
of inventing facts or using outside knowledge. Keep the answer concise and
refer to specific report sections or figures when useful.

Generated report:
{json.dumps(report, indent=2, default=str)}

Conversation history:
{json.dumps(history or [], indent=2)}

User question:
{question}
"""
    try:
        response = model.invoke(prompt)
    except Exception as exc:
        raise ValueError("Gemini could not answer the follow-up question.") from exc

    content = response.content
    if isinstance(content, str):
        return content.strip()
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and isinstance(block.get("text"), str)
    ).strip()
