"""
A module for holding currency-related information.
"""

# Default number of decimal places for display and common operations
DEFAULT_DISPLAY_DECIMAL_PLACES = 2

# Default maximum number of decimal places for internal calculations
DEFAULT_MAX_QUANTIZING_DECIMAL_PLACES = 6

# Absolute maximum number of decimal places supported (like types Decimal128)
ABSOLUTE_MAX_DECIMAL_PLACES = 34

# Dictionary to map currencies to their standard number of decimal places
CURRENCY_DECIMAL_PLACES = {
    "NO_CURRENCY": 2,
    "USD": 2,
    "CAD": 2,
    "BTC": 8,  # Bitcoin often uses 8 decimal places
    "MXN": 2,
    "EUR": 2,
    "INR": 0,
    "CLF": 4,
    "GBP": 2,
    "JPY": 0,
    "CNY": 2,
    "AUD": 2,
    "SGD": 2,
    "HKD": 2,
    "NZD": 2,
    "CHF": 2,
    "ZAR": 2,
    "BRL": 2,
    "RUB": 2,
    "TRY": 2,
    "THB": 2,
    "KRW": 0,
    "VND": 0,
    "PHP": 2,
    "IDR": 0,
    "MYR": 2,
    "BDT": 0,
    "NGN": 2,
    "ZMW": 2,
    "XAF": 0,
    "XOF": 0,
    "XCD": 2,
    "XDR": 2,
    "XAG": 2,
    "XAU": 2,
    "XPD": 2,
    "XPT": 2,
    "XTS": 2,
    "XXX": 2,
    "XBB": 2,
    "XBC": 2,
    "XBD": 2,
}

CURRENCY_SYMBOLS = {
    "USD": "$",
    "CAD": "$",
    "BTC": "₿",
    "MXN": "$",
    "EUR": "€",
    "INR": "₹",
    "GBP": "£",
    "JPY": "¥",
    "CNY": "¥",
    "AUD": "$",
    "SGD": "$",
    "HKD": "$",
    "NZD": "$",
    "CHF": "₣",
    "ZAR": "R",
    "BRL": "R$",
    "RUB": "₽",
    "TRY": "₺",
    "THB": "฿",
    "KRW": "₩",
    "VND": "₫",
    "PHP": "₱",
    "IDR": "Rp",
    "MYR": "RM",
    "BDT": "৳",
    "NGN": "₦",
    "ZMW": "ZK",
    "XAF": "FCFA",
    "XOF": "CFA",
    "XCD": "$",
    "XDR": "SDR",
    "XAG": "XAG",
    "XAU": "XAU",
    "XPD": "XPD",
    "XPT": "XPT",
    "XTS": "XTS",
    "XXX": "XXX",
    "XBB": "XBB",
    "XBC": "XBC",
    "XBD": "XBD",
}


def get_decimal_places(currency_code: str) -> int:
    """Get the number of decimal places for a given currency."""
    return CURRENCY_DECIMAL_PLACES.get(
        currency_code.upper(), DEFAULT_DISPLAY_DECIMAL_PLACES
    )


def get_currency_symbol(currency_code: str) -> str:
    return CURRENCY_SYMBOLS.get(currency_code.upper(), currency_code)
