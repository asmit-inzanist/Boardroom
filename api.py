# api.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from data_layer.prices import resolve_ticker
from orchestrator.graph import app as graph_app

api = FastAPI(title="Boardroom API")

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