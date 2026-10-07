# api.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from agents.follow_up_agent import FollowUpRateLimitError, answer_follow_up
from data_layer.prices import resolve_ticker
from data_layer.cache import get_cached
from orchestrator.graph import app as graph_app
from data_layer.reports import (
    get_latest_report,
    get_report_version,
    list_report_summaries,
    list_report_versions,
)

import os

load_dotenv()

api = FastAPI(title="Boardroom API")


class FollowUpRequest(BaseModel):
    ticker: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=1000)
    history: list[dict] = Field(default_factory=list)


# Allow your frontend (running on a different port/file) to call this API
api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5500,http://127.0.0.1:5500",
        ).split(",")
        if origin.strip()
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.get("/report/{ticker}")
def get_report(ticker: str):
    try:
        resolved = resolve_ticker(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        result = graph_app.invoke({
            "ticker": resolved["ticker"],
            "input_query": ticker,
            "company_name": resolved["company_name"],
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/reports")
def get_reports():
    try:
        return list_report_summaries()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@api.get("/reports/{ticker}")
def get_saved_report(ticker: str):
    try:
        report = get_latest_report(ticker.strip().upper())
        if not report:
            raise HTTPException(
                status_code=404,
                detail="No saved report is available for this company.",
            )
        return report
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@api.get("/reports/{ticker}/history")
def get_report_history(ticker: str):
    try:
        return list_report_versions(ticker.strip().upper())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@api.get("/reports/{ticker}/history/{version}")
def get_saved_report_version(ticker: str, version: int):
    try:
        report = get_report_version(ticker.strip().upper(), version)
        if not report:
            raise HTTPException(status_code=404, detail="Saved report version not found.")
        return report
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@api.post("/follow-up")
def follow_up(request: FollowUpRequest):
    report = get_latest_report(request.ticker.strip().upper())
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