# api.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from agents.follow_up_agent import FollowUpRateLimitError, answer_follow_up
from data_layer.prices import resolve_ticker
from data_layer.cache import get_cached
from orchestrator.graph import app as graph_app

api = FastAPI(title="Boardroom API")


class FollowUpRequest(BaseModel):
    ticker: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=1000)
    history: list[dict] = Field(default_factory=list)


# Allow your frontend (running on a different port/file) to call this API
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # fine for local dev; tighten later if deployed
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.get("/report/{ticker}")
def get_report(ticker: str):
    try:
        resolved = resolve_ticker(ticker)
        result = graph_app.invoke({
            "ticker": resolved["ticker"],
            "data_bundle": {},
            "agent_outputs": [],
            "disagreements": [],
            "disagreement_log": [],
            "final_report": {}
        })
        report = result["final_report"]
        report.setdefault("input_query", ticker)
        report.setdefault("company_name", resolved["company_name"])
        return report
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/follow-up")
def follow_up(request: FollowUpRequest):
    cached = get_cached(request.ticker.strip().upper())
    report = cached.get("final_report") if cached else None
    if not report:
        raise HTTPException(
            status_code=404,
            detail="No generated report is available for this company yet.",
        )

    try:
        answer = answer_follow_up(report, request.question.strip(), request.history)
        return {"answer": answer}
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except FollowUpRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc