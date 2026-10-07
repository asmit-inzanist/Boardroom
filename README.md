# Boardroom

Boardroom is an AI-assisted investment research terminal. It combines market data, financial statements, SEC filing excerpts where available, recent news, and multiple analyst agents into a single company research report.

## Features

- FastAPI backend with report, saved-report, history, and follow-up endpoints
- Company and ticker resolution through Yahoo Finance search and Gemini
- Market data and financial statements through `yfinance`
- SEC 10-K retrieval and parsing for eligible US companies
- Recent company news through Tavily
- Independent financial, business-model, competitive-risk, and management analysis
- Debate and synthesis steps for resolving disagreements between analysts
- Saved report history 

## Requirements

- Python 3.11 or newer
- PostgreSQL for saved reports
- API keys for Google Gemini, Groq, and Tavily
- Internet access to Yahoo Finance and the SEC

## Setup

Clone the repository and create a virtual environment:

```powershell
git clone https://github.com/asmit-inzanist/Boardroom.git
cd Boardroom
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create a local environment file from the template:

```powershell
Copy-Item .env.example .env
```

Add your credentials and database connection to `.env`:

```text
TAVILY_API_KEY=your-tavily-key
GROQ_ANALYST_API_KEY=your-groq-analyst-key
GROQ_ORCHESTRATOR_API_KEY=your-groq-orchestrator-key
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-3.1-flash-lite
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
```

`DATABASE_URL` is required for saving and loading reports. The daily fetched-data cache is created locally at `data/cache.db`.

Never commit `.env` or any API key. The repository `.gitignore` excludes local secrets, virtual environments, generated caches, and Python bytecode.

### SEC contact information

SEC requests use the `User-Agent` defined in `data_layer/filings.py`. Replace the placeholder with a descriptive application name and a real contact email address:

```python
HEADERS = {
    "User-Agent": "Boardroom Research your-email@example.com"
}
```

SEC filing access does not require an SEC login or API key. A valid contact identity and responsible request rate are required.

## Run the application

Start the API from the project root:

```powershell
uvicorn api:api --reload
```

In a second terminal, serve the frontend:

```powershell
python -m http.server 5500 --directory frontend
```

Open the frontend in a browser after both servers are running.

## Data pipeline

For a new company request, Boardroom:

1. Resolves a company name or ticker through Yahoo Finance search. Natural-language company names may first be normalized by Gemini.
2. Fetches approximately one year of price history and available financial data from Yahoo Finance.
3. Calculates revenue growth, earnings growth, margins, debt, cash flow, and related metrics.
4. Attempts to retrieve the latest SEC 10-K and stores a filing excerpt when the ticker is present in the SEC database.
5. Fetches recent company news through Tavily.
6. Sends the resulting bundle to the analyst agents, debate stage, and final synthesizer.
7. Saves the generated report to PostgreSQL and the fetched daily bundle to the local SQLite cache.

The cache is keyed by ticker and date. A same-day cache hit avoids fetching fresh market data, filings, and news. Clear the cache before testing updated source data:

```powershell
python -c "from data_layer.cache import clear_cache; clear_cache()"
```

To clear one ticker:

```powershell
python -c "from data_layer.cache import clear_cache; clear_cache('AAPL')"
```

## Data coverage and limitations

Boardroom is designed primarily for publicly traded companies covered by Yahoo Finance. It can support many international listings when Yahoo Finance has a valid exchange ticker, such as `TCS.NS` or `7203.T`.

Data is not guaranteed for every company:

- Private companies do not have public market prices, analyst targets, or Yahoo Finance financial statements.
- Yahoo Finance may provide incomplete financial fields for small or international listings.
- SEC data is US-specific. Non-US companies may not have an SEC 10-K available.
- Tavily may return limited or no recent news for smaller companies.
- Ambiguous company names can resolve to an unrelated listing or fund. Fund and ETF-like matches are rejected for normal company searches.

When an SEC filing is unavailable, the report can still use Yahoo Finance and Tavily data, but filing-based management and governance analysis may be less detailed. Source availability is recorded in the report metadata.

## Reports and report history

Completed reports are stored in PostgreSQL. Each new report is saved as a separate version rather than replacing older reports.

The Reports page is lazy-loaded:

- Opening **Reports** loads lightweight company summaries only.
- Opening a company folder loads report-file metadata for that ticker.
- Opening a report file loads the full contents of that specific report.

This keeps the initial Reports page fast and avoids loading every full report at once.

## Project structure

```text
.
├── agents/          Analyst and report-synthesis agents
├── data/             Local runtime cache (ignored by Git)
├── data_layer/       Market data, filings, news, reports, and cache helpers
├── frontend/         Browser interface
├── orchestrator/     LangGraph workflow and debate resolution
├── tools/            Shared analysis calculations
├── api.py            FastAPI application
├── .env.example      Environment variable template
└── requirements.txt  Python dependencies
```

## Disclaimer

Boardroom is a research and educational tool, not financial advice. Verify all information independently before making investment decisions.
