import json
import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import yfinance as yf

load_dotenv()


def _gemini_company_name(user_input: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    model = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        google_api_key=api_key,
        temperature=0,
        timeout=30,
    )
    try:
        response = model.invoke(
            f"""Identify the publicly traded company the user is asking about.
Return only the company's commonly recognized name, with no explanation,
ticker, punctuation, or JSON.

User input:
{user_input}"""
        )
    except Exception as exc:
        raise ValueError("Gemini could not extract a company name from the input.") from exc
    content = response.content
    if isinstance(content, str):
        company_name = content.strip()
    else:
        company_name = "".join(
            block if isinstance(block, str) else str(block.get("text", ""))
            for block in content
            if isinstance(block, (str, dict))
        ).strip()

    if company_name.startswith("{"):
        try:
            company_name = str(json.loads(company_name)["company_name"]).strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Gemini returned an invalid company name.") from exc

    company_name = company_name.strip("\"'")
    if not company_name:
        raise ValueError("Gemini could not identify a company from the input.")
    return company_name


def resolve_ticker(query: str) -> dict[str, str]:
    """Resolve any user input through Gemini, then validate it with Yahoo Finance."""
    if not query.strip():
        raise ValueError("Enter a ticker or company name.")

    search_query = _gemini_company_name(query)

    try:
        quotes = yf.Search(search_query, max_results=10).quotes
    except Exception as exc:
        raise ValueError(f"Could not resolve '{query}' as a company or ticker.") from exc

    equity_quotes = [
        quote for quote in quotes
        if quote.get("quoteType") == "EQUITY" and quote.get("symbol")
    ]
    if not equity_quotes:
        raise ValueError(
            f"No listed company was found for '{query}'. Try a company name or ticker."
        )

    preferred_exchanges = {"NMS", "NYQ", "ASE", "NASDAQ", "NYSE"}
    equity_quotes.sort(
        key=lambda quote: (
            quote.get("exchange") in preferred_exchanges,
            float(quote.get("score", 0) or 0),
        ),
        reverse=True,
    )
    selected = equity_quotes[0]
    return {
        "ticker": str(selected["symbol"]).upper(),
        "company_name": str(
            selected.get("longname") or selected.get("shortname") or selected["symbol"]
        ),
    }


def get_price_history(ticker: str, period="1y"):
    stock = yf.Ticker(ticker)
    return stock.history(period=period)


def get_financials(ticker: str):
    stock = yf.Ticker(ticker)
    return {
        "income_statement": stock.financials,
        "balance_sheet": stock.balance_sheet,
        "cash_flow": stock.cashflow,
        "info": stock.info  # includes P/E, market cap, EPS, etc. pre-calculated
    }


def _row_values(dataframe, labels: tuple[str, ...]) -> dict[str, float]:
    """Return finite numeric values from the first matching financial-statement row."""
    if dataframe is None or dataframe.empty:
        return {}

    row_name = next((label for label in labels if label in dataframe.index), None)
    if row_name is None:
        return {}

    values = {}
    for period, value in dataframe.loc[row_name].items():
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number == number and abs(number) != float("inf"):
            values[str(period.date() if hasattr(period, "date") else period)] = number
    return values


def _growth(values: dict[str, float]) -> dict[str, float]:
    periods = sorted(values.items(), key=lambda item: item[0])
    result = {}
    for index in range(1, len(periods)):
        previous_period, previous = periods[index - 1]
        current_period, current = periods[index]
        if previous:
            result[f"{previous_period}_to_{current_period}"] = (current - previous) / abs(previous)
    return result


def calculate_financial_metrics(financials: dict) -> dict:
    """Derive report-ready metrics from the statements already fetched."""
    income = financials["income_statement"]
    balance = financials["balance_sheet"]
    cash_flow = financials["cash_flow"]

    revenue = _row_values(income, ("Total Revenue", "Operating Revenue"))
    net_income = _row_values(income, ("Net Income", "Net Income Common Stockholders"))
    operating_income = _row_values(income, ("Operating Income",))
    total_debt = _row_values(balance, ("Total Debt",))
    cash = _row_values(balance, ("Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"))
    operating_cash_flow = _row_values(
        cash_flow, ("Operating Cash Flow", "Total Cash From Operating Activities")
    )
    capital_expenditure = _row_values(
        cash_flow, ("Capital Expenditure", "Capital Expenditure Reported")
    )

    free_cash_flow = {
        period: operating_cash_flow[period] - abs(capital_expenditure.get(period, 0))
        for period in operating_cash_flow
    }

    return {
        "revenue": revenue,
        "revenue_growth": _growth(revenue),
        "net_income": net_income,
        "earnings_growth": _growth(net_income),
        "operating_income": operating_income,
        "margins": {
            "operating": {
                period: operating_income[period] / revenue[period]
                for period in operating_income
                if period in revenue and revenue[period]
            },
            "net": {
                period: net_income[period] / revenue[period]
                for period in net_income
                if period in revenue and revenue[period]
            },
        },
        "debt": {
            "total_debt": total_debt,
            "cash": cash,
            "net_debt": {
                period: total_debt[period] - cash.get(period, 0)
                for period in total_debt
            },
        },
        "cash_flow": {
            "operating_cash_flow": operating_cash_flow,
            "capital_expenditure": capital_expenditure,
            "free_cash_flow": free_cash_flow,
        },
    }