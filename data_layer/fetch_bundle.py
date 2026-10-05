# data_layer/fetch_bundle.py

import json
from datetime import datetime, timezone

from data_layer.prices import calculate_financial_metrics, get_price_history, get_financials
from data_layer.filings import get_latest_10k_text
from data_layer.news import get_recent_news
from data_layer.cache import get_cached, save_cache, init_db


def _dataframe_to_jsonable(dataframe) -> dict:
    """Convert a pandas DataFrame while preserving date indexes and columns."""
    return json.loads(
        dataframe.to_json(
            orient="split",
            date_format="iso",
            date_unit="ms",
        )
    )


def fetch_bundle(ticker: str) -> dict:
    """
    Single entry point for all agent data.
    Checks cache first; only hits real APIs if today's data isn't already saved.
    """
    init_db()  # safe to call every time, only creates table if missing

    cached = get_cached(ticker)
    if cached and "analysis_metrics" in cached:
        print(f"[cache hit] Using cached data for {ticker}")
        return cached

    print(f"[cache miss] Fetching fresh data for {ticker}")

    price_data = get_price_history(ticker)
    financials = get_financials(ticker)
    filing_text = get_latest_10k_text(ticker)
    news = get_recent_news(ticker)
    info = financials["info"]

    bundle = {
        "ticker": ticker,
        "metadata": {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "sources": ["yfinance", "SEC 10-K", "Tavily news"],
        },
        "price_data": _dataframe_to_jsonable(price_data),
        "financials": {
            "income_statement": _dataframe_to_jsonable(financials["income_statement"]),
            "balance_sheet": _dataframe_to_jsonable(financials["balance_sheet"]),
            "cash_flow": _dataframe_to_jsonable(financials["cash_flow"]),
            "info": info,
        },
        "analysis_metrics": {
            **calculate_financial_metrics(financials),
            "valuation": {
                key: info.get(key)
                for key in (
                    "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months",
                    "enterpriseToEbitda", "enterpriseToRevenue", "marketCap",
                    "trailingEps", "freeCashflow", "profitMargins", "operatingMargins",
                    "debtToEquity",
                )
            },
            "analyst_consensus": {
                key: info.get(key)
                for key in (
                    "recommendationKey", "recommendationMean",
                    "numberOfAnalystOpinions",
                )
            },
            "target_price": {
                key: info.get(key)
                for key in (
                    "targetMeanPrice", "targetMedianPrice",
                    "targetHighPrice", "targetLowPrice",
                )
            },
        },
        "filing_excerpt": filing_text[:5000],  # truncate — full filings are too long, refine later
        "news": news,
    }

    save_cache(ticker, bundle)
    return bundle