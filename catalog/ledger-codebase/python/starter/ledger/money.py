"""Currencies and display formatting."""

# How many digits after the decimal point each booked currency has.
# Every amount in the ledger is an integer count of minor units (cents, fils, yen).
MINOR_DIGITS = {"EUR": 2, "GBP": 2, "JPY": 0, "KWD": 3, "USD": 2}


def valid_currency(cur: str) -> bool:
    """True if the ledger books amounts in cur."""
    return cur in MINOR_DIGITS


def format_amount(minor: int, cur: str) -> str:
    """Render minor units for display: format_amount(-1250, "USD") is "-12.50 USD"."""
    sign = "-" if minor < 0 else ""
    minor = abs(minor)
    d = MINOR_DIGITS[cur]
    if d == 0:
        return f"{sign}{minor} {cur}"
    whole, frac = divmod(minor, 10**d)
    return f"{sign}{whole}.{frac:0{d}d} {cur}"
