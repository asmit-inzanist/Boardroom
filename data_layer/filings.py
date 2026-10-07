# data_layer/filings.py

from bs4 import BeautifulSoup
import requests
import re

HEADERS = {"User-Agent": "blockfeed0@gmail.comsa"}  # replace with your real name/email — SEC requires this


def get_cik(ticker: str) -> str:
    """Look up a company's CIK number from its ticker."""
    resp = requests.get(
        "https://www.sec.gov/files/company_tickers.json",
        headers=HEADERS
    )
    resp.raise_for_status()
    data = resp.json()
    for entry in data.values():
        if entry["ticker"].upper() == ticker.upper():
            return str(entry["cik_str"]).zfill(10)  # SEC wants CIK zero-padded to 10 digits
    raise ValueError(f"Ticker {ticker} not found in SEC ticker list")


def get_filings_list(cik: str) -> dict:
    """Get a company's full filing history metadata."""
    resp = requests.get(
        f"https://data.sec.gov/submissions/CIK{cik}.json",
        headers=HEADERS
    )
    resp.raise_for_status()
    return resp.json()


def get_latest_10k_url(cik: str) -> str | None:
    """Find the URL of the most recent 10-K filing document."""
    filings = get_filings_list(cik)["filings"]["recent"]
    for i, form in enumerate(filings["form"]):
        if form == "10-K":
            accession = filings["accessionNumber"][i].replace("-", "")
            doc_name = filings["primaryDocument"][i]
            cik_int = int(cik)
            return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/{doc_name}"
    return None



def get_latest_10k_text(ticker: str) -> str:
    cik = get_cik(ticker)
    url = get_latest_10k_url(cik)
    if url is None:
        raise ValueError(f"No 10-K found for {ticker}")
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove hidden XBRL metadata, scripts, and styles — none of this is human-readable content
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    for tag in soup.find_all(style=True):
        style = tag.get("style")
        if isinstance(style, str) and "display:none" in style.replace(" ", ""):
            tag.decompose()
    for tag in soup.find_all(re.compile(r"^ix:(header|hidden)")):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Collapse excessive blank lines left behind
    text = "\n".join(line for line in text.splitlines() if line.strip())

    return text # raw HTML — still needs cleanup, but it's a string now