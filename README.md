# Boardroom

Boardroom is an AI-assisted investment research terminal. It combines financial data, SEC filing excerpts, recent news, and multiple analyst agents into a single company research report.

## Features

- FastAPI backend with a `GET /report/{ticker}` endpoint
- Financial data and price history through `yfinance`
- SEC filing retrieval and parsing
- Recent news search through Tavily
- Independent financial, business model, risk, and management analysis
- Debate and synthesis steps for resolving disagreements between analysts
- Browser-based frontend for searching companies and viewing reports

## Requirements

- Python 3.11 or newer
- API keys for:
  - Google Gemini
  - Groq
  - Tavily

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

Add your credentials to `.env`:

```text
TAVILY_API_KEY=your-tavily-key
GROQ_ANALYST_API_KEY=your-groq-analyst-key
GROQ_ORCHESTRATOR_API_KEY=your-groq-orchestrator-key
GEMINI_API_KEY=your-gemini-key
```

Never commit `.env` or any API key. The repository `.gitignore` excludes local secrets, virtual environments, and the generated SQLite cache.

## Run the application

Start the API from the project root:

```powershell
uvicorn api:api --reload
```

The API is available at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs`.

In a second terminal, serve the frontend:

```powershell
python -m http.server 5500 --directory frontend
```

Open `http://localhost:5500` in a browser. The frontend is configured to call the API at `http://localhost:8000/report/`.

## API usage

Request a report by ticker:

```text
GET http://localhost:8000/report/AAPL
```

The endpoint accepts a ticker symbol or a company name that can be resolved by the backend. A successful response contains the synthesized report as JSON.

## Project structure

```text
.
├── agents/          Analyst and report-synthesis agents
├── data/             Local runtime cache (ignored by Git)
├── data_layer/       Market data, filings, news, and cache helpers
├── frontend/         Browser interface
├── orchestrator/     LangGraph workflow and debate resolution
├── tools/            Shared analysis calculations
├── api.py            FastAPI application
├── .env.example      Environment variable template
└── requirements.txt  Python dependencies
```

## Development checks

Compile all project Python files before opening a pull request:

```powershell
python -m compileall -q .
```

The `myvenv/` directory, `.env`, generated caches, and Python bytecode are intentionally excluded from version control.

## Disclaimer

Boardroom is a research and educational tool, not financial advice. Verify all information independently before making investment decisions.
