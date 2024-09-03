from __future__ import annotations

# Standard library imports
import functools
import re
import warnings
from decimal import ROUND_HALF_DOWN, Decimal, localcontext
from numbers import Number
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    Iterable,
)

# Library we need to support custom serializations
from pydantic_core import core_schema

# Local application imports
from precise_money.currency import (
    CURRENCY_SYMBOLS,
    CURRENCY_DECIMAL_PLACES,
    DEFAULT_DISPLAY_DECIMAL_PLACES,
    DEFAULT_MAX_QUANTIZING_DECIMAL_PLACES,
    ABSOLUTE_MAX_DECIMAL_PLACES,
)
from precise_money.error import MoneyError


# Default decimal precision for all monetary value calculations
DECIMAL_PRECISION = 28

# ISO 4217 conversion factor for currency representation
ISO_CONVERSION_FACTOR = 10000

# Values for quantizing Decimals that support to 35 decimal places
DECIMAL_PLACE_QUANTIZING_DECIMALS = {i: Decimal(f"1e-{i}") for i in range(35)}

# For readability, we explicitly define the most common ones:
DECIMAL_PLACE_QUANTIZING_DECIMALS.update(
    {
        0: Decimal("0."),
        1: Decimal("0.1"),
        2: Decimal("0.01"),  # USD, CAD, MXN, EUR
        3: Decimal("0.001"),
        4: Decimal("0.0001"),
        5: Decimal("0.00001"),
        6: Decimal("0.000001"),
        8: Decimal("0.00000001"),  # For cryptocurrencies
    }
)
# You can access these like:
# DECIMAL_PLACE_QUANTIZING_DECIMALS[2]  # Returns Decimal('0.01')
# DECIMAL_PLACE_QUANTIZING_DECIMALS[34] # Returns Decimal('1E-34')

NULL_CURRENCY_CODE = "NO_CURRENCY"

T = TypeVar("T", bound=Callable)


def decimal_context(fn: T) -> T:
    """
    A decorator that sets a specific decimal precision for the decorated function.

    This decorator creates a local decimal context with a predefined precision
    (DECIMAL_PRECISION) for the execution of the decorated function. It ensures
    consistent and precise decimal arithmetic without the need to manually set
    the precision in multiple places throughout the code.

    Args:
        fn (Callable): The function to be decorated.

    Returns:
        Callable: A wrapped version of the input function that executes within
        the specified decimal precision context.

    Example:
        @decimal_context
        def calculate_interest(principal: Decimal, rate: Decimal, time: int) -> Decimal:
            return principal * (1 + rate) ** time

    Notes:
        - The precision is set to DECIMAL_PRECISION (usually 28) for all calculations
          within the decorated function.
        - This decorator is particularly useful for financial calculations where
          consistent precision is crucial.
        - It uses Python's decimal.localcontext() to temporarily set the precision,
          ensuring that it doesn't affect calculations outside the decorated function.
        - The original function's metadata (name, docstring, etc.) is preserved using
          functools.wraps.

    Warning:
        While this decorator ensures high precision, be aware that it may impact
        performance for functions that are called frequently with simple calculations.
        Use it judiciously, particularly for complex or critical financial computations.
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            return fn(*args, **kwargs)

    return cast(T, wrapper)


@decimal_context
def quantize_decimal(
    value: Decimal,
    decimal_places: int = DEFAULT_MAX_QUANTIZING_DECIMAL_PLACES,
    rounding: str = ROUND_HALF_DOWN,
) -> Decimal:
    """
    Quantize a Decimal value to a specified number of decimal places.

    This function adjusts the precision of a Decimal value by adding or removing
    decimal places to match the specified `decimal_places` value. It's primarily
    used internally by the Money class to ensure consistent precision across
    monetary values.

    Args:
        value (Decimal): The Decimal value to quantize.
        decimal_places (int, optional): The desired number of decimal places.
            Defaults to DEFAULT_MAX_QUANTIZING_DECIMAL_PLACES.
        rounding (str, optional): The rounding method to use when quantizing.
            Should be one of the rounding modes defined in the `decimal` module
            (e.g., ROUND_HALF_UP, ROUND_HALF_DOWN, ROUND_DOWN, etc.).
            Defaults to ROUND_HALF_DOWN.

    Returns:
        Decimal: A new Decimal value quantized to the specified number of decimal places.

    Raises:
        ValueError: If an invalid rounding mode is specified.

    Note:
        This function is primarily intended for internal use by the Money class.
        Direct use is generally not necessary unless you're extending the Money class
        or need precise control over Decimal quantization.

    Examples:
        >>> from decimal import Decimal, ROUND_HALF_UP
        >>> quantize_decimal(Decimal('10.1234'), 2)
        Decimal('10.12')
        >>> quantize_decimal(Decimal('10.1254'), 2, ROUND_HALF_UP)
        Decimal('10.13')

    If the specified number of decimal places is not in the predefined
    DECIMAL_PLACE_QUANTIZING_DECIMALS dictionary, it falls back to
    DEFAULT_MAX_QUANTIZING_DECIMAL_PLACES.
    """
    if decimal_places < 0 or decimal_places > ABSOLUTE_MAX_DECIMAL_PLACES:
        raise MoneyError(
            f"decimal_places must be between 0 and {ABSOLUTE_MAX_DECIMAL_PLACES}",
            MoneyError.DECIMAL_PLACES_OUT_OF_RANGE,
        )

    # Get the quantizing decimal, defaulting to 1e-{decimal_places} if not in the dictionary
    decimal_places_decimal = DECIMAL_PLACE_QUANTIZING_DECIMALS.get(
        decimal_places, Decimal(f"1e-{decimal_places}")
    )

    try:
        return value.quantize(decimal_places_decimal, rounding=rounding)
    except Exception as e:
        raise MoneyError(
            f"Invalid quantization operation: {e}",
            MoneyError.INVALID_QUANTIZATION,
        )


class Money:
    """
    A robust container for handling monetary values with currency awareness.

    The Money class provides a safe and consistent way to store, modify, compare,
    and serialize monetary values. While it may appear more verbose than using
    simple `int`s or `Decimal`s, it offers several critical advantages:

    1. Currency-aware comparisons: Ensures that only monetary values of the same
       currency are compared, preventing logical errors.
    2. Precise decimal representation: Uses `Decimal` internally to avoid
       floating-point rounding errors common with floats.
    3. Correct rounding: Automatically rounds to the appropriate number of
       decimal places for the given currency during serialization.
    4. String serialization: Provides string representations to maintain precision
       and readability, especially important for financial data.
    5. Normalization: Offers options to normalize inputs, useful when dealing with
       integer cents or other non-decimal representations.
    6. Rounding: Allows for custom rounding behavior, useful for certain calculations
       such as tax, margin, or total calculations.

    The preferred method for creating Money instances is `from_currency`:

    Example:
        amount = "20"
        amount_in_dollars = Money.from_currency("USD", amount)
        amount_in_dollars_str = amount_in_dollars.as_string()
        assert amount_in_dollars_str == "20.00"

    This class supports various arithmetic operations, comparisons, and
    provides multiple serialization options to suit different use cases.
    It's designed to be compatible with popular Python ORMs and serialization
    libraries, making it ideal for use in financial applications, e-commerce
    systems, or any scenario requiring precise handling of monetary values.
    """

    __slots__ = (
        "_value",
        "_currency_code",
        "decimal_places",
        "rounding",
    )

    def __init__(
        self,
        value: Decimal,
        currency_code: str = "USD",
        decimal_places: int = DEFAULT_DISPLAY_DECIMAL_PLACES,
        rounding: str = ROUND_HALF_DOWN,
    ):
        self._value = value
        self._currency_code = currency_code
        self.decimal_places = decimal_places
        self.rounding = rounding

    @property
    def currency_symbol(self) -> str:
        try:
            return CURRENCY_SYMBOLS[self.currency_code]
        except KeyError:
            return self.currency_code

    @property
    def currency_code(self) -> str:
        return self._currency_code

    @property
    def currency_conversion_num(self) -> int:
        """
        Return the currency conversion number for the Money object.
        """
        return cast(int, 10**self.decimal_places)

    @property
    def value(self) -> Decimal:
        return self._value

    @staticmethod
    def validate_currency_code(currency_code: str) -> str:
        """Validate and return the uppercase currency code."""
        upper_code = currency_code.upper()
        if not re.match(r"^[A-Z]{3}$", upper_code) and upper_code != NULL_CURRENCY_CODE:
            raise MoneyError(
                f"Invalid currency code: {currency_code}",
                MoneyError.INVALID_CURRENCY_CODE,
            )
        if upper_code not in CURRENCY_SYMBOLS:
            raise MoneyError(
                f"Invalid currency code: {currency_code}",
                MoneyError.INVALID_CURRENCY_CODE,
            )
        return upper_code

    @classmethod
    @decimal_context
    def from_currency(
        cls,
        currency_code: str,
        amount: Union[str, Decimal, int],
        normalize: bool = False,
        quantize: Optional[bool] = None,
        rounding: str = ROUND_HALF_DOWN,
    ) -> Money:
        """
        Create a Money object from a currency code and an amount.

        This method is the primary factory method for creating Money objects. It handles
        various input formats and applies normalization and quantization as needed.

        Args:
            currency_code (str): The ISO 4217 currency code (e.g., "USD", "EUR").
            amount (Union[str, Decimal, int]): The monetary amount. Can be a string, Decimal, or integer.
            normalize (bool, optional): If True, divide the amount by 10^decimal_places.
                Use this when working with integer representations of decimal amounts (e.g., cents).
                Defaults to False.
            quantize (Optional[bool], optional): If True, round to the currency's standard decimal places.
                If False, no rounding is performed. If None (default), rounding is performed.
            rounding (str, optional): The rounding method to use when quantizing.
                Should be one of the rounding modes from the decimal module
                (e.g., ROUND_HALF_UP, ROUND_HALF_DOWN). Defaults to ROUND_HALF_DOWN.

        Returns:
            Money: A new Money object representing the specified amount in the given currency.

        Raises:
            ValueError: If a non-zero amount is provided with the NULL_CURRENCY_CODE.
            KeyError: If an invalid currency code is provided (fallback to default decimal places).

        Examples:
            >>> Money.from_currency("USD", "10.50")
            <USD: 10.50>

            >>> Money.from_currency("USD", 1050, normalize=True)
            <USD: 10.50>

            >>> Money.from_currency("JPY", "1050")
            <JPY: 1050>

        Notes:
            - The `normalize` parameter is useful when working with APIs or databases that represent
            monetary amounts as integers (e.g., cents for USD).
                * An API might send 2000 to represent $20.00 (2000 cents)
                * A database might store 1234567 to represent $12,345.67
            - The `quantize` parameter allows for creating Money objects without rounding, which
            can be useful in certain calculation scenarios where maintaining maximum precision
            is important.
            - If the currency code is not recognized, the method falls back to a default number
            of decimal places (usually 2).
            - The NULL_CURRENCY_CODE("") is a special case used to represent zero amounts
            without a specific currency. It can only be used with a zero amount.

        See Also:
            Money.from_iso_currency: For creating Money objects from ISO 4217 integer representations.
        """
        currency_code = currency_code.upper()
        try:
            decimal_places = CURRENCY_DECIMAL_PLACES[currency_code]
        except KeyError:
            decimal_places = DEFAULT_DISPLAY_DECIMAL_PLACES
        value = Decimal(amount)
        if normalize:
            value = value / (10**decimal_places)
        # quantizing will round the value to the meaningful number of decimal places
        # for the Money's currency
        do_quantize = True
        if quantize is False:
            do_quantize = False

        if do_quantize:
            # configure the decimal places to the currency's decimal places
            value = quantize_decimal(value, decimal_places, rounding=rounding)

        if currency_code == NULL_CURRENCY_CODE and value != 0:
            raise MoneyError(
                "Non-zero money must have a currency supplied when you try to create Money from_currency",
                error_key=MoneyError.MISSING_CURRENCY,
            )

        return cls(
            value=value,
            currency_code=currency_code,
            decimal_places=decimal_places,
            rounding=rounding,
        )

    @staticmethod
    @decimal_context
    def zero(currency_code: str = NULL_CURRENCY_CODE) -> Money:
        """
        Create a Money object representing zero in the specified currency.

        This method provides a convenient way to create a Money object with a value of zero.
        It's particularly useful when initializing sums, representing the absence of money,
        or as a starting point for calculations.

        Args:
            currency_code (str, optional): The ISO 4217 currency code (e.g., "USD", "EUR").
                Defaults to NULL_CURRENCY_CODE(typically "").

        Returns:
            Money: A new Money object representing zero in the specified currency.

        Examples:
            >>> Money.zero()
            <---: 0.00 USD>

            >>> Money.zero("USD")
            <USD: 0.00>

            >>> Money.zero("JPY")
            <JPY: 0>

        Notes:
            - When used with NULL_CURRENCY_CODE(default), it represents a generic zero
            amount without a specific currency.
            - The resulting Money object will have the appropriate number of decimal places
            for the specified currency (e.g., 2 for USD, 0 for JPY).
            - This method uses `from_iso_currency` internally with `quantize=False` to ensure
            the zero value is represented precisely without any rounding.

        See Also:
            Money.from_currency: For creating non-zero Money objects.
            Money.from_iso_currency: For creating Money objects from ISO 4217 integer representations.
        """
        return Money.from_iso_currency(currency_code, 0, quantize=False)

    @staticmethod
    def _parse_string_amount(value: str) -> Decimal:
        """
        Parse a string representation of a monetary amount.

        This method handles various formats including:
        - Standard: 1234.56
        - Comma as decimal: 1234,56
        - Thousands separator with dot: 1.234,56
        - Thousands separator with comma: 1,234.56
        - No decimal part: 1234

        Args:
            value (str): The string representation of the monetary amount.

        Returns:
            Decimal: The parsed decimal value.

        Raises:
            ValueError: If the string cannot be parsed as a valid monetary value.
        """
        # Remove currency symbols, spaces, and other non-numeric characters
        value = re.sub(r"[^\d,.-]", "", value)

        # Count occurrences of commas and dots
        comma_count = value.count(",")
        dot_count = value.count(".")
        comma_index = value.find(",")
        period_index = value.find(".")
        if comma_count == 1 and dot_count == 0:
            # Format: 1234,56 (comma as decimal separator)
            value = value.replace(",", ".")
        elif comma_count > 1 and dot_count == 0:
            # Format: 1,234,567 (comma as thousands separator, no decimal part)
            value = value.replace(",", "")
        elif dot_count > 1 and comma_count == 0:
            # Format: 1.234.567 (dot as thousands separator, no decimal part)
            value = value.replace(".", "")
        elif comma_count > 0 and dot_count == 1:
            if comma_index < period_index:
                # Format: 1,234.56 (comma as thousands separator, dot as decimal)
                value = value.replace(",", "")
                # return Decimal(value)
            else:
                # Format: 1.234,56 (dot as thousands separator, comma as decimal)
                value = value.replace(".", "").replace(",", ".")
        try:
            return Decimal(value)
        except Exception:
            raise MoneyError(
                f"Unable to parse '{value}' as a valid monetary value",
                error_key=MoneyError.INVALID_MONETARY_VALUE,
            )

    @staticmethod
    def from_db_value(
        value: Union[Decimal, str, int, Any],
        currency: str = "USD",
        normalize: bool = False,
        quantize: Optional[bool] = None,
        rounding: str = ROUND_HALF_DOWN,
    ) -> "Money":
        """
        Create a Money object from a database value

        This method is particularly useful when working with MongoDB or other databases
        that may store decimal values in various formats. It provides a standardized way
        to convert database-stored values into Money objects.

        Args:
            value: The value from the database. Can be one of:
                    - bson.decimal128.Decimal128 (pymongo's Decimal128 type, which we handle with Any)
                    - decimal.Decimal
                    - str (will be cleaned of '$' and ',' characters)
                    - int or float
            currency (str): The currency code for the monetary value. Defaults to "USD".

        Returns:
            Money: A new Money object representing the input value in the specified currency.

        Raises:
            ValueError: If the input cannot be converted to a valid decimal value.

        Examples:
            # For a regular Decimal or float from a standard database
            >>> money = Money.from_db_value(Decimal('10.99'), 'USD')
            >>> print(money)
            10.99 USD

            # For a Decimal128 value from pymongo (not dependency in this package)
            >>> from bson.decimal128 import Decimal128
            >>> mongo_value = Decimal128('15.75')
            >>> money = Money.from_db_value(mongo_value, 'EUR')
            >>> print(money)
            15.75 EUR

            # For a string value (e.g., from a CSV import)
            >>> money = Money.from_db_value('$1,234.56', 'CAD')
            >>> print(money)
            1234.56 CAD

        Notes:
            - The method also handles string inputs, removing currency symbols and thousands separators,
                which can be helpful when importing data from various sources.
            - While primarily designed for database interactions, this method can be used as a general-purpose
                converter for creating Money objects from various numeric representations.
        """

        if isinstance(value, Decimal):
            decimal_value = value
        elif hasattr(value, "to_decimal"):  # Handle Decimal128 without direct import
            decimal_value = value.to_decimal()
        elif isinstance(value, (int, float)):
            decimal_value = Decimal(str(value))
        elif isinstance(value, str):
            decimal_value = Money._parse_string_amount(value)
        else:
            raise TypeError(f"Unsupported type for monetary value: {type(value)}")
        return Money.from_currency(
            currency,
            decimal_value,
            normalize=normalize,
            quantize=quantize,
            rounding=rounding,
        )

    @staticmethod
    def from_decimal128(value: Any, currency: str = "USD") -> "Money":
        # when you know the value is a Decimal128
        assert isinstance(value, Any)
        return Money.from_currency(currency, value.to_decimal())

    @classmethod
    @decimal_context
    def from_iso_currency(
        cls,
        currency_code: str,
        amount: int,
        quantize: Optional[bool] = None,
    ) -> Money:
        """
        Create a Money object from an ISO 4217 currency code and an integer amount.

        This method converts an integer representation of a monetary amount (as per ISO 4217 standards)
        to a Money object. It's particularly useful when working with financial systems or APIs
        that represent currency amounts as integers.

        Args:
            currency_code (str): The ISO 4217 currency code (e.g., "USD", "EUR").
            amount (int): The monetary amount as an integer, typically representing the smallest
                unit of the currency (e.g., cents for USD). This value is divided by ISO_CONVERSION_FACTOR
                (usually 10000) to convert it to the standard decimal representation.
            quantize (Optional[bool], optional): If True, round to the currency's standard decimal places.
                If False, no rounding is performed. If None (default), use the default quantization
                behavior of Money.from_currency.

        Returns:
            Money: A new Money object representing the specified amount in the given currency.

        Examples:
            >>> Money.from_iso_currency("USD", 1234567)
            <USD: 123.46>

            >>> Money.from_iso_currency("JPY", 1234567)
            <JPY: 123>

            >>> Money.from_iso_currency("USD", 1234567, quantize=False)
            <USD: 123.4567>

        Notes:
            - The ISO_CONVERSION_FACTOR is typically 10000, allowing for up to 4 decimal places
            as per ISO 4217 standards.
            - This method first converts the integer amount to a decimal by dividing by ISO_CONVERSION_FACTOR,
            then uses Money.from_currency to create the final Money object.
            - The actual number of decimal places in the result depends on the currency and the
            quantize parameter.
            - For currencies with no decimal places (e.g., JPY), the result will be rounded to a whole number
            if quantize is True or None.

        See Also:
            Money.from_currency: The underlying method used to create the Money object.

        Raises:
            ValueError: If the currency_code is invalid or if the resulting value is invalid for the currency.
        """
        value = amount / ISO_CONVERSION_FACTOR
        return cls.from_currency(currency_code, Decimal(value), quantize=quantize)

    def _is_same_currency(self, other: Money) -> None:
        if self._currency_code != other._currency_code:
            raise MoneyError(
                f"Unable to operate on different currencies: {self._currency_code}, {other._currency_code}",
                error_key=MoneyError.CURRENCY_MISMATCH,
            )

    @decimal_context
    def apply_operation(
        self,
        operation: Callable[[Decimal], Decimal],
        quantize: bool = True,
        rounding: str = ROUND_HALF_DOWN,
    ) -> Money:
        """
        Apply a custom operation to the Money object's value and return a new Money instance.

        This method allows for flexible manipulation of the monetary value while maintaining
        currency information and precision. It's useful for performing custom calculations
        that aren't covered by the standard arithmetic operations.

        Args:
            operation (Callable[[Decimal], Decimal]): A function that takes a Decimal as input
                and returns a Decimal. This function defines the operation to be performed
                on the monetary value.
            quantize (bool, optional): Whether to round the resulting value to the currency's
                standard number of decimal places. Defaults to True.
            rounding (str, optional): The rounding mode to use. Defaults to ROUND_HALF_DOWN.

        Returns:
            Money: A new Money instance with the result of the operation, in the same currency.

        Example:
            >>> usd = Money.from_currency("USD", "20")
            >>> half_usd = usd.apply_operation(lambda x: x / 2)
            >>> print(half_usd)
            10.00 USD

            >>> def apply_tax(amount: Decimal) -> Decimal:
            ...     return amount * Decimal('1.08')  # 8% tax
            >>> with_tax = usd.apply_operation(apply_tax)
            >>> print(with_tax)
            21.60 USD

        Note:
            - The provided operation should be pure and only operate on the Decimal value.
            - This method does not modify the original Money instance.
            - If the operation could result in a loss of precision, consider setting
            quantize=False and handling the rounding manually.
        """
        new_value = operation(self._value)
        new_money = self.from_currency(
            self._currency_code, new_value, quantize=quantize, rounding=rounding
        )
        return new_money

    @decimal_context
    def cmp(self, other: Money, cmp_func: Callable[[Decimal, Decimal], bool]) -> bool:
        """
        Perform a custom comparison between this Money object and another using a provided comparison function.

        This method allows for flexible comparisons between two Money objects of the same currency.
        It's useful for implementing custom comparison logic that goes beyond the standard
        equality and ordering operations.

        Args:
            other (Money): Another Money object to compare with this one.
            cmp_func (Callable[[Decimal, Decimal], bool]): A function that takes two Decimal
                values as input and returns a boolean. This function defines the comparison
                operation to be performed on the two monetary values.

        Returns:
            bool: The result of the comparison function.

        Raises:
            MoneyError: If the currencies of the two Money objects don't match.

        Example:
            >>> usd_10 = Money.from_currency("USD", "10")
            >>> usd_20 = Money.from_currency("USD", "20")

            # Check if the difference is greater than 5
            >>> def diff_gt_5(a: Decimal, b: Decimal) -> bool:
            ...     return abs(a - b) > Decimal('5')

            >>> result = usd_10.cmp(usd_20, diff_gt_5)
            >>> print(result)  # Output: True

            # Check if the ratio is within a certain range
            >>> def ratio_in_range(a: Decimal, b: Decimal) -> bool:
            ...     ratio = a / b if b != 0 else Decimal('inf')
            ...     return Decimal('0.4') < ratio < Decimal('0.6')

            >>> result = usd_10.cmp(usd_20, ratio_in_range)
            >>> print(result)  # Output: True

        Note:
            - The provided comparison function should be pure and only operate on the Decimal values.
            - This method does not modify the original Money instances.
            - Both Money objects must have the same currency.
            - Use this method when standard comparison operators (<, >, ==, etc.) are not sufficient
            for your specific comparison needs.
        """
        self._is_same_currency(other)
        res = cmp_func(self._value, other._value)
        return res

    @decimal_context
    def sum(self, moneys: Iterable[Money]) -> Money:
        """
        Calculate the sum of an iterable of Money objects.

        This method provides a way to sum Money objects that is compatible with
        static type checkers like mypy. It assumes all Money objects in the
        iterable have the same currency.

        Args:
            moneys (Iterable[Money]): An iterable (e.g., list, tuple, generator)
                of Money objects to be summed. All objects are assumed to have
                the same currency.

        Returns:
            Money: A new Money object representing the sum of all input Money objects.
                   If the input iterable is empty, returns a zero Money object.

        Examples:
            >>> usd_10 = Money.from_currency("USD", "10")
            >>> usd_20 = Money.from_currency("USD", "20")
            >>> usd_30 = Money.from_currency("USD", "30")
            >>> total = Money.sum([usd_10, usd_20, usd_30])
            >>> print(total)
            60.00 USD

            >>> empty_sum = Money.sum([])
            >>> print(empty_sum)
            0.00 USD

        Note:
            - This method assumes all Money objects in the iterable have the same currency.
              It's the caller's responsibility to ensure this condition is met.
            - This method is particularly useful when working with large collections of
              Money objects or when using libraries that expect a sum function.
            - It's more type-safe than the built-in sum() function when working with Money objects.
        """
        return functools.reduce(
            lambda acc, money: acc + money, moneys, self.__class__.zero()
        )

    @property
    def is_neg(self) -> bool:
        # returns true if the value is negative
        return self._value < 0

    @property
    def is_pos(self) -> bool:
        # returns true if the value is positive
        return self._value > 0

    def __abs__(self) -> Money:
        if self.is_neg:
            return -self
        return self

    @property
    def is_zero(self) -> bool:
        cmp = self._value == 0
        return cmp

    def __repr__(self) -> str:
        return f"Currency {self.currency_code}: {self.as_string()}"

    def __str__(self) -> str:
        return f"{self.as_string()} {self.currency_code}"

    def __float__(self) -> float:
        return self.as_float()

    def __eq__(self, other: object) -> bool:
        """
        Check if two Money objects are equal.

        Returns True if the objects have the same currency and value, False otherwise.
        """
        if not other:
            return False
        if isinstance(other, Money):
            try:
                self._is_same_currency(other)
                return self.value == other.value
            except MoneyError:
                return False
        return False

    def __lt__(self, other: Money) -> bool:
        """
        Check if this Money object is less than another.

        Raises:
            MoneyError: If currencies don't match.
        """
        self._is_same_currency(other)
        return self.as_iso_int() < other.as_iso_int()

    def __le__(self, other: Money) -> bool:
        """
        Check if this Money object is less than or equal to another.

        Raises:
            MoneyError: If currencies don't match.
        """
        self._is_same_currency(other)
        return self.as_iso_int() <= other.as_iso_int()

    def __ge__(self, other: Money) -> bool:
        """
        Check if this Money object is greater than or equal to another.

        Raises:
            MoneyError: If currencies don't match.
        """
        self._is_same_currency(other)
        return self.as_iso_int() >= other.as_iso_int()

    def __gt__(self, other: Money) -> bool:
        """
        Check if this Money object is greater than another.

        Raises:
            MoneyError: If currencies don't match.
        """
        self._is_same_currency(other)
        return self.as_iso_int() > other.as_iso_int()

    def __add__(self, other: Money) -> Money:
        """
        Add two Money objects of the same currency.

        This method overloads the '+' operator for Money objects, allowing for
        intuitive addition of monetary values.

        Args:
            other (Money): Another Money object to be added to this one.

        Returns:
            Money: A new Money object representing the sum of the two Money objects.

        Raises:
            MoneyError: If the currencies of the two Money objects don't match.

        Notes:
            - The addition is performed using ISO integer representations to avoid
            floating-point arithmetic errors.
            - The result is always quantized (rounded) to ensure consistency and
            avoid subtle rounding errors that can occur in decimal arithmetic.

        Example:
            >>> usd_10 = Money.from_currency("USD", "10.00")
            >>> usd_5 = Money.from_currency("USD", "5.00")
            >>> result = usd_10 + usd_5
            >>> print(result)
            15.00 USD

        Warning:
            Adding Money objects with different currencies will raise an error.
            Always ensure you're adding Money objects of the same currency.
        """
        # Ensure both Money objects have the same currency
        self._is_same_currency(other)

        # Convert both Money objects to their ISO integer representations
        a = self.as_iso_int()
        b = other.as_iso_int()
        res = a + b
        return self.__class__.from_iso_currency(
            other._currency_code, res, quantize=True
        )

    def __sub__(self, other: Money) -> Money:
        """
        Subtract one Money object from another of the same currency.

        This method overloads the '-' operator for Money objects, allowing for
        intuitive subtraction of monetary values.

        Args:
            other (Money): The Money object to be subtracted from this one.

        Returns:
            Money: A new Money object representing the difference between the two Money objects.

        Raises:
            MoneyError: If the currencies of the two Money objects don't match.

        Notes:
            - The subtraction is performed using ISO integer representations to avoid
            floating-point arithmetic errors.
            - The result is always quantized (rounded) to ensure consistency and
            avoid subtle rounding errors that can occur in decimal arithmetic.

        Example:
            >>> usd_20 = Money.from_currency("USD", "20.00")
            >>> usd_5 = Money.from_currency("USD", "5.00")
            >>> result = usd_20 - usd_5
            >>> print(result)
            15.00 USD

        Warning:
            Subtracting Money objects with different currencies will raise an error.
            Always ensure you're subtracting Money objects of the same currency.
        """
        self._is_same_currency(other)
        a = self.as_iso_int()
        b = other.as_iso_int()
        res = a - b
        return self.__class__.from_iso_currency(
            other._currency_code, res, quantize=True
        )

    def __neg__(self) -> Money:
        """
        Negate the Money object, effectively changing its sign.

        This method overloads the unary '-' operator for Money objects, allowing for
        intuitive negation of monetary values.

        Returns:
            Money: A new Money object with the same absolute value but opposite sign.

        Notes:
            - Negation is performed by simply changing the sign of the internal value.
            - The result is quantized (rounded) to ensure consistency with other operations,
            even though negation itself doesn't affect significant digits.

        Example:
            >>> usd_10 = Money.from_currency("USD", "10.00")
            >>> negated = -usd_10
            >>> print(negated)
            -10.00 USD

        This operation is useful for representing debits or when reversing transactions.
        """
        return self.from_currency(self._currency_code, -self._value, quantize=True)

    @decimal_context
    def __mul__(self, other: Union[int, float, Decimal]) -> Money:
        """
        Multiplies the current `Money` instance by a given number and returns a new `Money` instance.

        This method allows you to perform multiplication of a `Money` object by an integer, float, or Decimal value,
        resulting in a new `Money` object with the product value.

        Args:
            other (Union[int, float, Decimal]): The number to multiply with. It can be an integer, a floating-point number,
            or a Decimal. This value will be converted to a Decimal for the multiplication operation.

        Returns:
            Money: A new `Money` instance with the result of the multiplication. The currency code remains the same
            as the original `Money` instance, and the resulting value is quantized according to the currency's rules.

        Raises:
            NotImplementedError: If `other` is not an instance of `int`, `float`, `Decimal`, or `Number`.

        Examples:
            >>> money = Money.from_currency('USD', Decimal('10.00'))
            >>> result = money * 2
            >>> print(result)
            Money(USD, Decimal('20.00'))

            >>> result = money * Decimal('1.5')
            >>> print(result)
            Money(USD, Decimal('15.00'))
        """
        if not isinstance(other, Number):
            return NotImplemented
        mult = self._value * Decimal(other)
        return self.__class__.from_currency(self._currency_code, mult, quantize=True)

    @decimal_context
    def __truediv__(self, other: Union[int, float, Decimal]) -> Money:
        """
        Divide the Money object by a number.

        Args:
            other: The divisor (int, float, or Decimal).

        Returns:
            A new Money object with the divided value.

        Raises:
            TypeError: If the divisor is not a number.
        """
        if not isinstance(other, Number):
            return NotImplemented
        return self.__class__.from_currency(
            self._currency_code, self._value / Decimal(other), quantize=True
        )

    @decimal_context
    def as_string(self) -> str:
        """
        Return a formatted string representation of the monetary value.
        """
        return f"{self._value:,.{self.decimal_places}f}"

    @decimal_context
    def as_float(self) -> float:
        """
        Convert to float, with a warning for potential precision loss.
        """
        value = float(quantize_decimal(self._value, self.decimal_places))
        if abs(self._value) > 1e15 or abs(self._value) < 1e-15:
            warnings.warn(
                "Converting to float may result in loss of precision", RuntimeWarning
            )
        return value

    @decimal_context
    def as_display_string(self) -> str:
        """
        Return a formatted string with currency symbol for display purposes.
        """
        formatted = self.as_string()
        return f"{self.currency_symbol}{formatted}"

    @decimal_context
    def as_currency_smallest_unit_int(self) -> int:
        """
        Return the value as an integer in the smallest currency unit (e.g., cents).

        Example:
            amount = Money.from_currency("USD", "12.342288")
            amount.as_currency_smallest_unit_int() # returns 1235
        """
        value = quantize_decimal(self._value, self.decimal_places, self.rounding)
        return int(value * self.currency_conversion_num)

    @decimal_context
    def as_iso_int(self) -> int:
        """
        Return the value as an ISO 4217 compliant integer representation.
        """
        value = quantize_decimal(self._value, self.decimal_places)
        return int(value * ISO_CONVERSION_FACTOR)

    @classmethod
    def from_iso_currency_fields(
        cls,
        currency_field: str,
        amount_field: str,
        custom_field: Optional[str] = None,
    ) -> Callable[[dict], Any]:
        """
        Create a function to construct Money objects from ISO currency fields in a dictionary.

        Useful for integrating with systems using ISO 4217 currency representations.
        """
        if custom_field is not None:

            def _from_iso_currency_opt(data: dict) -> Optional[Money]:
                if data.get(custom_field) is not None:
                    return Money.from_iso_currency(
                        data[currency_field], data[amount_field]
                    )
                return None

            return _from_iso_currency_opt
        else:

            def _from_iso_currency(data: dict) -> Money:
                return cls.from_iso_currency(data[currency_field], data[amount_field])

            return _from_iso_currency

    @staticmethod
    def from_dict(
        data: dict,
        currency_field: str,
        amount_field: str,
        normalize: bool = False,
        custom_field: Optional[str] = None,
    ) -> Callable[[dict], Any]:
        """
        Create a function to construct Money objects from dictionary fields.

        Useful for integrating with ORMs or serialization libraries.
        """
        if custom_field:
            if parsed := data.get(custom_field, None):
                return Money.from_currency(
                    parsed[currency_field],
                    parsed[amount_field],
                    normalize=normalize,
                )
            else:
                raise ValueError(f"Missing custom field: {custom_field} - data: {data}")
        else:
            return Money.from_currency(
                data[currency_field], data[amount_field], normalize=normalize
            )

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
        """
        The new (version > 2) way to support custom serialization and validation with Pydantic.
        https://docs.pydantic.dev/latest/concepts/types/#customizing-validation-with-__get_pydantic_core_schema__
        """
        return core_schema.with_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls.serialize
            ),
        )

    @classmethod
    def _validate(cls: Type[Any], value: Union[Money, dict], context: Any) -> Money:
        """
        Validator method for Pydantic, Odmantic model integration.

        This method is used by Pydantic (and by dependency Odmantic) when the Money class is used as a field
        in a Pydantic model. It ensures that Money objects are properly constructed
        from either existing Money instances or dictionary representations.

        Args:
            cls: The Money class.
            value (Union[Money, dict]): The value to be validated. Can be either
                a Money instance or a dictionary containing Money data.
            context: The context in which the validation is occurring.

        Returns:
            Money: A valid Money instance.

        This method allows seamless integration with Pydantic's serialization
        and deserialization processes, maintaining the integrity of Money objects
        throughout these operations.

        """
        if isinstance(value, Money):
            return value
        elif isinstance(value, tuple):
            return cls(amount=value[0], currency=value[1])
        elif isinstance(value, dict):
            return cls.deserialize(value)

        raise ValueError(f"Invalid value type: {type(value)}")

    @classmethod
    @decimal_context
    def deserialize(cls, data: Dict[str, Union[int, str]]) -> Money:
        """
        Convert a dictionary with money values to a properly formatted money object.
        """
        if isinstance(data, dict):
            for f, v in data.items():
                try:
                    Money._parse_string_amount(v)
                    amount_field = f
                except Exception:
                    currency_field = f

            return cls.from_dict(data, currency_field, amount_field)
        else:
            raise MoneyError(f"Unhandled data type: type - {type(data)} data -{data}")

    @decimal_context
    def serialize(self) -> Dict[str, Union[int, str]]:
        """
        Convert the Money object to a dictionary representation for serialization.
        """
        return {
            "value": self.as_string(),
            "currency_code": self._currency_code,
        }
