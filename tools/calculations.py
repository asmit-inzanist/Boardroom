# tools/calculations.py
from decimal import Decimal

def pe_ratio(price: Decimal, eps: Decimal) -> Decimal:
    if eps == 0:
        raise ValueError("EPS cannot be zero")
    return price / eps

def pb_ratio(price: Decimal, book_value_per_share: Decimal) -> Decimal:
    if book_value_per_share == 0:
        raise ValueError("Book value per share cannot be zero")
    return price / book_value_per_share

def verify_market_cap(price: Decimal, shares_outstanding: Decimal, reported_value: Decimal) -> dict:
    calculated = price * shares_outstanding
    deviation_pct = abs(calculated - reported_value) / reported_value * 100
    return {
        "calculated": calculated,
        "reported": reported_value,
        "deviation_pct": deviation_pct,
        "flagged": deviation_pct > Decimal("1.0")  # more than 1% off = worth checking
    }

def simple_dcf(cash_flows: list[Decimal], discount_rate: Decimal, terminal_growth: Decimal) -> Decimal:
    npv = Decimal("0")
    for year, cf in enumerate(cash_flows, start=1):
        npv += cf / ((1 + discount_rate) ** year)
    terminal_value = cash_flows[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
    npv += terminal_value / ((1 + discount_rate) ** len(cash_flows))
    return npv