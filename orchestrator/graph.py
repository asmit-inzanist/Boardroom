from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END
from agents.synthesizer_agent import synthesize_report
from data_layer.fetch_bundle import fetch_bundle
from data_layer.cache import save_cache

from agents.financial_agent import run_financials_agent
from agents.business_model_agent import run_business_model_agent
from agents.risk_agent import run_risk_agent
from agents.management_agent import run_management_agent
from orchestrator.debate import find_disagreements_llm, run_debate_turn

class states(TypedDict):
    ticker: str
    data_bundle: dict
    agent_outputs: Annotated[list, operator.add]
    disagreements: list
    disagreement_log: list
    final_report: dict

def fetch_data_node(state: states) -> dict:
    bundle = fetch_bundle(state["ticker"])
    return {
        "data_bundle": bundle
    }
def financials_node(state: states) -> dict:
    result = run_financials_agent(state["data_bundle"])
    return {
        "agent_outputs": [result.model_dump()]
    }
def business_model_node(state: states) -> dict:
    result = run_business_model_agent(state["data_bundle"])
    return {
        "agent_outputs": [result.model_dump()]
    }
def risk_node(state: states) -> dict:
    result = run_risk_agent(state["data_bundle"])
    return {
        "agent_outputs": [result.model_dump()]
    }

def management_node(state: states) -> dict:
    result = run_management_agent(state["data_bundle"])
    return {
        "agent_outputs": [result.model_dump()]
    }

# orchestrator/graph.py — extended

def disagreement_node(state: states) -> dict:
    disagreements = find_disagreements_llm(state["agent_outputs"])
    return {"disagreements": disagreements}

def debate_node(state: states) -> dict:
    log = []
    for a, b in state["disagreements"]:
        response_a = run_debate_turn(a, b)
        response_b = run_debate_turn(b, a)
        log.append({"pair": [a["agent"], b["agent"]], "responses": [response_a, response_b]})
    return {"disagreement_log": log}

def synthesizer_node(state: states) -> dict:
    report = synthesize_report(
        state["ticker"],
        state["data_bundle"],
        state["agent_outputs"],
        state["disagreement_log"],
    )
    cached_bundle = dict(state["data_bundle"])
    cached_bundle["final_report"] = report
    save_cache(state["ticker"], cached_bundle)
    return {"final_report": report}

graph = StateGraph(states)

graph.add_node("fetch_data", fetch_data_node)
graph.add_node("financials", financials_node)
graph.add_node("business_model", business_model_node)
graph.add_node("risk", risk_node)
graph.add_node("management", management_node)
graph.add_node("disagreement", disagreement_node)
graph.add_node("debate", debate_node)
graph.add_node("synthesizer", synthesizer_node)

graph.set_entry_point("fetch_data")

# fan-out: all 4 run in parallel after fetch_data
graph.add_edge("fetch_data", "financials")
graph.add_edge("fetch_data", "business_model")
graph.add_edge("fetch_data", "risk")
graph.add_edge("fetch_data", "management")

# fan-in: all 4 must finish before disagreement detection runs
graph.add_edge("financials", "disagreement")
graph.add_edge("business_model", "disagreement")
graph.add_edge("risk", "disagreement")
graph.add_edge("management", "disagreement")

graph.add_edge("disagreement", "debate")
graph.add_edge("debate", "synthesizer")
graph.add_edge("synthesizer", END)

app=graph.compile()
