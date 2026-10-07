import os

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

load_dotenv()


def save_report(
    ticker: str,
    report: dict,
    input_query: str | None = None,
    company_name: str | None = None,
) -> None:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    with psycopg.connect(database_url) as connection:
        connection.execute(
            """
            INSERT INTO public.reports (
                ticker,
                input_query,
                company_name,
                report_data
            )
            VALUES (%s, %s, %s, %s)
            """,
            (ticker, input_query, company_name, Jsonb(report)),
        )


def get_latest_report(ticker: str) -> dict | None:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            """
            SELECT report_data
            FROM public.reports
            WHERE ticker = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (ticker,),
        ).fetchone()

    return row[0] if row else None


def list_report_versions(ticker: str) -> list[dict]:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    with psycopg.connect(database_url) as connection:
        rows = connection.execute(
            """
            SELECT created_at, input_query, company_name
            FROM public.reports
            WHERE ticker = %s
            ORDER BY created_at DESC
            """,
            (ticker,),
        ).fetchall()

    return [
        {
            "version": index,
            "created_at": created_at.isoformat(),
            "input_query": input_query,
            "company_name": company_name or ticker,
        }
        for index, (created_at, input_query, company_name) in enumerate(rows)
    ]


def get_report_version(ticker: str, version: int) -> dict | None:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    if version < 0:
        return None

    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            """
            SELECT report_data
            FROM public.reports
            WHERE ticker = %s
            ORDER BY created_at DESC
            LIMIT 1 OFFSET %s
            """,
            (ticker, version),
        ).fetchone()

    return row[0] if row else None


def list_report_summaries() -> list[dict]:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    with psycopg.connect(database_url) as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT ON (ticker)
                ticker,
                report_data,
                created_at
            FROM public.reports
            ORDER BY ticker, created_at DESC
            """
        ).fetchall()

    return [
        {
            "ticker": ticker,
            "company_name": report_data.get("company_name") or ticker,
            "created_at": created_at.isoformat(),
        }
        for ticker, report_data, created_at in rows
    ]