"""
A module for holding error classes.
"""


class BaseError(Exception):
    def __init__(self, message: str, error_key: str):
        self.message = message
        self.error_key = error_key
        super().__init__(self.message)


class MoneyError(BaseError):
    MISSING_CURRENCY = "MISSING_CURRENCY"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    INVALID_QUANTIZATION = "INVALID_QUANTIZATION"
    DECIMAL_PLACES_OUT_OF_RANGE = "DECIMAL_PLACES_OUT_OF_RANGE"
    INVALID_MONETARY_VALUE = "INVALID_MONETARY_VALUE"
    INVALID_CURRENCY_CODE = "INVALID_CURRENCY_CODE"
