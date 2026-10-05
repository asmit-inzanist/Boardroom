# data_layer/news.py

import os
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()  # reads variables from a .env file into the environment

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def get_recent_news(ticker: str, days: int = 14) -> list[dict]:
    results = client.search(
        query=f"{ticker} stock news",
        days=days,
        max_results=10
    )
    return results.get("results", [])