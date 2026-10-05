import sqlite3, json, os
from datetime import date


def init_db():
    os.makedirs("data", exist_ok=True)
    with sqlite3.connect("data/cache.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                ticker TEXT NOT NULL,
                fetch_date TEXT NOT NULL,
                data TEXT NOT NULL,
                PRIMARY KEY (ticker, fetch_date)
            )
        """)
        conn.commit()


def get_cached(ticker: str) -> dict | None:
    with sqlite3.connect("data/cache.db") as conn:
        row = conn.execute(
            "SELECT data FROM cache WHERE ticker=? AND fetch_date=?",
            (ticker, str(date.today()))
        ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except json.JSONDecodeError:
        return None


def save_cache(ticker: str, data: dict):
    with sqlite3.connect("data/cache.db") as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cache (ticker, fetch_date, data) VALUES (?, ?, ?)",
            (ticker, str(date.today()), json.dumps(data, default=str))
        )
        conn.commit()


def clear_cache(ticker: str | None = None):
    with sqlite3.connect("data/cache.db") as conn:
        if ticker:
            conn.execute("DELETE FROM cache WHERE ticker=?", (ticker,))
        else:
            conn.execute("DELETE FROM cache")
        conn.commit()