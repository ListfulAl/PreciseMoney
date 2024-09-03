# PreciseMoney

A Python library for handling monetary values and currencies with maniacal attention to precision. PreciseMoney offers robust tools for financial calculations and currency management, ensuring accuracy in even the most complex monetary operations. Perfect for developers who lose sleep over floating-point errors.

## Features

- Pydantic support via serialization and deserialization
- Precise decimal arithmetic for monetary calculations
- Support for multiple currencies
- Currency-aware comparisons and arithmetic operations
- Easy-to-use API for creating and manipulating monetary values

## Installation

You can install the Money Library using pip:

```python
pip install precise_money
```

If you are using pipenv, you can install the Money Library using pipenv:

```python
pipenv install precise_money
```

## Quick Start

Here's a simple example of how to use the precise_money Library:

```python
from precise_money.money import Money

# Create money objects
usd_50 = Money.from_currency("USD", "50.00")
usd_30 = Money.from_currency("USD", "30.00")

# Perform arithmetic operations
total = usd_50 + usd_30
print(total)  # Output: 80.00 USD

# Compare money objects
print(usd_50 > usd_30)  # Output: True

# Format as string
print(usd_50.as_string())  # Output: 50.00

# Get currency symbol
print(usd_50.currency_symbol)  # Output: $
```

## Advanced Usage: High-Precision Calculations

The library provides a `decimal_context` decorator for high-precision calculations. Here's an example of how to use it:

```python
from decimal import Decimal
from precise_money.money import decimal_context, DECIMAL_PRECISION

@decimal_context
def calculate_compound_interest(principal: Decimal, rate: Decimal, time: int) -> Decimal:
    return principal * (1 + rate) ** time

# Usage
principal = Decimal("1000.00")
rate = Decimal("0.05")
time = 10

result = calculate_compound_interest(principal, rate, time)

print(f"Initial principal: ${principal}")
print(f"Annual interest rate: {rate:.2%}")
print(f"Time period: {time} years")
print(f"Final amount: ${result:.2f}")
print(f"Calculation precision: {DECIMAL_PRECISION} decimal places")

# Output:
# Initial principal: $1000.00
# Annual interest rate: 5.00%
# Time period: 10 years
# Final amount: $1628.89
# Calculation precision: 28 decimal places
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Resources

- [Currency Codes from OpenData @ Github](https://github.com/datasets/currency-codes)

- [ISO Currency Standards](https://en.wikipedia.org/wiki/ISO_4217)

- [Rounding](https://docs.python.org/3/library/decimal.html#rounding-modes)

### Currency Formatting

Currencies around the world use different formatting conventions. For example, the currency symbol can appear before or after the amount, and the decimal separator can be a comma or a period.

This is important when you are recieving values from APIs or extracting values from databases that are not in a consistent format. This library includes tooling to help you handle these cases, and you should `Money._parse_string_amount` to handle your special cases. I tried to handle most sane cases, but most people are insane so be prudent about checking what you are getting from your APIs.

U.S. currency is formatted with a decimal point (.) as a separator between dollars and cents. Some countries use a comma (,) instead of a decimal point to indicate the separation. In addition, while the U.S. and a number of other countries use a comma to separate thousands, some countries use a decimal point for this purpose.

To help you identify the formatting for currency, below is a table of countries and their respective currency formats.

Examples:

- 500 or 500,00 or 500.00 = five hundred dollars and no cents
- 500,15 or 500.15 = five hundred dollars and fifteen cents
- 500,150 or 500.150 or 500,150.00 or 500.150,00 = five hundred thousand, one hundred fifty dollars and no cents

| Currency (ISO)           | Comma for cents | Dot for cents | Comma for thousands | Dot for thousands |
| ------------------------ | --------------- | ------------- | ------------------- | ----------------- |
| USD (US Dollar)          | No              | Yes           | Yes                 | No                |
| EUR (Euro)               | Varies\*        | Varies\*      | Varies\*            | Varies\*          |
| GBP (British Pound)      | No              | Yes           | Yes                 | No                |
| JPY (Japanese Yen)\*\*   | N/A             | N/A           | Yes                 | No                |
| CHF (Swiss Franc)        | No              | Yes           | Yes                 | No                |
| CAD (Canadian Dollar)    | No              | Yes           | Yes                 | No                |
| AUD (Australian Dollar)  | No              | Yes           | Yes                 | No                |
| CNY (Chinese Yuan)       | No              | Yes           | Yes                 | No                |
| INR (Indian Rupee)       | No              | Yes           | Yes                 | No                |
| BRL (Brazilian Real)     | Yes             | No            | No                  | Yes               |
| RUB (Russian Ruble)      | Yes             | No            | No                  | Yes               |
| SEK (Swedish Krona)      | Yes             | No            | No                  | Yes               |
| NOK (Norwegian Krone)    | Yes             | No            | No                  | Yes               |
| DKK (Danish Krone)       | Yes             | No            | No                  | Yes               |
| PLN (Polish Złoty)       | Yes             | No            | No                  | Yes               |
| ZAR (South African Rand) | No              | Yes           | Yes                 | No                |
| MXN (Mexican Peso)       | No              | Yes           | Yes                 | No                |
| SGD (Singapore Dollar)   | No              | Yes           | Yes                 | No                |
| HKD (Hong Kong Dollar)   | No              | Yes           | Yes                 | No                |
| NZD (New Zealand Dollar) | No              | Yes           | Yes                 | No                |

\* EUR usage varies by country. Some use comma for cents and dot for thousands (e.g., Germany, France), while others use the opposite (e.g., Ireland, Malta).

\*\* JPY typically doesn't use decimal places in everyday transactions.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. My primary focus is on [Autaly](https://autaly.co/) however I will review and merge PRs that are beneficial to the community.

I'd like to keep the library as simple as possible and avoid adding too much complexity. But if you need to make an addition and includes a dependency, please include it in the `Pipfile` and `Pipfile.lock` so that it can be installed via `pip`. To update requirements.txt, run

```bash
pipenv requirements > requirements.txt
```

Building and publishing to PyPI

```bash
python setup.py sdist
twine upload dist/*

```

Be sure to add unit tests for your code.

```bash
pytest tests
pytest tests/test_money.py::TestMoney::test_addition
```
