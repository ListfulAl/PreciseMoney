# Standard library imports
import unittest
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN, ROUND_DOWN

# Local application imports
from precise_money.currency import get_decimal_places, get_currency_symbol
from precise_money.error import MoneyError
from precise_money.money import Money, quantize_decimal
from typing import Union, Optional


class TestCurrency(unittest.TestCase):

    def test_get_decimal_places(self):
        self.assertEqual(get_decimal_places("USD"), 2)
        self.assertEqual(get_decimal_places("BTC"), 8)

    def test_get_currency_symbol(self):
        self.assertEqual(get_currency_symbol("USD"), "$")
        self.assertEqual(get_currency_symbol("BTC"), "₿")


class TestQuantize(unittest.TestCase):
    def test_quantize_decimal(self):
        self.assertEqual(
            quantize_decimal(Decimal("12.3456"), 5, ROUND_HALF_DOWN), Decimal("12.3456")
        )
        # the 56 is more than half way to the next integer, so it should round up to 12.35
        self.assertEqual(
            quantize_decimal(Decimal("12.3456"), 2, ROUND_HALF_DOWN), Decimal("12.35")
        )
        self.assertEqual(
            quantize_decimal(Decimal("12.3450"), 2, ROUND_HALF_DOWN), Decimal("12.34")
        )
        self.assertEqual(
            quantize_decimal(Decimal("12.3456"), 2, ROUND_DOWN), Decimal("12.34")
        )


class TestMoney(unittest.TestCase):
    def test_creation(self):
        m = Money.from_currency("USD", "10.00")
        self.assertEqual(str(m), "10.00 USD")

    def test_instance_creation_with_child_class(self):
        class CustomMoney(Money):
            def __init__(self, amount, currency="USD"):
                super().__init__(amount, currency)

            @classmethod
            def from_currency(
                cls,
                currency_code: str,
                amount: Union[str, Decimal, int],
                normalize: bool = False,
                quantize: Optional[bool] = None,
                rounding: str = ROUND_HALF_DOWN,
            ):
                # a terrible function to test if this works
                return cls(
                    amount=Decimal("1.00"),
                    currency=currency_code,
                )

        m = CustomMoney.from_currency("USD", "10.00")
        self.assertEqual(str(m), "1.00 USD")
        self.assertIsInstance(m, CustomMoney)
        # testing addition should be new instance of CustomMoney
        m2 = CustomMoney.from_currency("USD", "10.00")
        m3 = m + m2
        self.assertIsInstance(m3, CustomMoney)
        self.assertEqual(str(m3), "1.00 USD")

    def test_creation_with_different_types(self):
        self.assertEqual(str(Money.from_currency("USD", 10)), "10.00 USD")
        self.assertEqual(str(Money.from_currency("USD", Decimal("10.00"))), "10.00 USD")

    def test_creation_with_quantize(self):
        self.assertEqual(
            str(
                Money.from_currency(
                    "USD", Decimal("10.0089"), quantize=True, rounding=ROUND_HALF_UP
                )
            ),
            "10.01 USD",
        )
        self.assertEqual(
            str(
                Money.from_currency(
                    "USD", Decimal("10.00500"), quantize=True, rounding=ROUND_HALF_DOWN
                )
            ),
            "10.00 USD",
        )

    def test_abs(self):
        m = Money.from_currency("USD", "-10.00")
        self.assertEqual(str(abs(m)), "10.00 USD")
        self.assertTrue(abs(m).is_pos)
        self.assertTrue(m.is_neg)

    def test_zero_creation(self):
        zero = Money.zero()
        self.assertEqual(str(zero), "0.00 NO_CURRENCY")
        self.assertTrue(zero.is_zero)
        zero = Money.zero("USD")
        self.assertEqual(str(zero), "0.00 USD")
        self.assertTrue(zero.is_zero)

    def test_from_db_value(self):
        self.assertEqual(str(Money.from_db_value(Decimal("10.00"))), "10.00 USD")
        self.assertEqual(str(Money.from_db_value("$10.00")), "10.00 USD")
        one_hundred_thousand = Money.from_db_value("100,000.00", "USD")
        self.assertEqual(str(one_hundred_thousand), "100,000.00 USD")
        self.assertEqual(one_hundred_thousand.value, Decimal("100000.00"))
        one_hundred_thousand = Money.from_db_value("100.000,00")
        self.assertEqual(one_hundred_thousand.value, Decimal("100000.00"))
        self.assertEqual(str(Money.from_db_value("10,00", "EUR")), "10.00 EUR")
        self.assertEqual(str(Money.from_db_value("500,15", "AUD")), "500.15 AUD")

    def test_addition(self):
        m1 = Money.from_currency("USD", "10.00")
        m2 = Money.from_currency("USD", "20.00")
        result = m1 + m2
        self.assertEqual(str(result), "30.00 USD")

    def test_subtraction(self):
        m1 = Money.from_currency("USD", "30.00")
        m2 = Money.from_currency("USD", "20.00")
        result = m1 - m2
        self.assertEqual(str(result), "10.00 USD")

    def test_multiplication(self):
        m = Money.from_currency("USD", "10.00")
        result = m * 3
        self.assertEqual(str(result), "30.00 USD")

    def test_division(self):
        m = Money.from_currency("USD", "30.00")
        result = m / 3
        self.assertEqual(str(result), "10.00 USD")

    def test_comparison(self):
        m1 = Money.from_currency("USD", "10.00")
        m2 = Money.from_currency("USD", "20.00")
        self.assertTrue(m1 < m2)
        self.assertTrue(m2 > m1)
        self.assertTrue(m1 <= m1)
        self.assertTrue(m1 >= m1)
        self.assertFalse(m1 == m2)

    def test_currency_mismatch(self):
        m1 = Money.from_currency("USD", "10.00")
        m2 = Money.from_currency("BTC", "10.00")
        with self.assertRaises(MoneyError):
            m1 + m2
        with self.assertRaises(MoneyError):
            m1 < m2
        with self.assertRaises(MoneyError):
            m1 - m2

    def test_normalization(self):
        m = Money.from_currency("USD", 1000, normalize=True)
        self.assertEqual(str(m), "10.00 USD")

    def test_as_string(self):
        m = Money.from_currency("USD", "1234.56")
        self.assertEqual(m.as_string(), "1,234.56")

    def test_as_float(self):
        m = Money.from_currency("USD", "1234.56")
        self.assertAlmostEqual(m.as_float(), 1234.56)

    def test_as_display_string(self):
        m = Money.from_currency("USD", "1234.56")
        self.assertEqual(m.as_display_string(), "$1,234.56")

    def test_as_currency_smallest_unit_int(self):
        m = Money.from_currency("USD", "12.348", rounding=ROUND_HALF_UP)
        self.assertEqual(m.as_currency_smallest_unit_int(), 1235)
        m = Money.from_currency("USD", "12.342", rounding=ROUND_HALF_DOWN)
        self.assertEqual(m.as_currency_smallest_unit_int(), 1234)

    def test_apply_operation(self):
        m = Money.from_currency("USD", "12.3456")
        m = m.apply_operation(lambda x: x / 2)
        self.assertEqual(str(m), "6.17 USD")
        m = Money.from_currency("USD", "12.3456")
        m = m.apply_operation(
            lambda x: x * Decimal("1.5"), quantize=True, rounding=ROUND_HALF_UP
        )
        self.assertEqual(str(m), "18.53 USD")

    def test_validate_currency_code(self):
        with self.assertRaises(MoneyError):
            Money.validate_currency_code("banana")
        with self.assertRaises(MoneyError):
            Money.validate_currency_code("whe")
        self.assertEqual(Money.validate_currency_code("usd"), "USD")

    def test_from_dict(self):
        data = {"currency_code": "USD", "value": "12.34"}
        m = Money.from_dict(data, "currency_code", "value")
        self.assertEqual(str(m), "12.34 USD")
        data = {
            "other_data": "blah blah",
            "custom_field": {"currency_code": "USD", "value": "12.34"},
        }
        m2 = Money.from_dict(
            data, "currency_code", "value", custom_field="custom_field"
        )
        self.assertEqual(str(m2), "12.34 USD")

    def test_as_iso_int(self):
        m = Money.from_currency("USD", "12.3456")
        self.assertEqual(m.as_iso_int(), 123500)

    def test_from_iso_currency(self):
        m = Money.from_iso_currency("USD", 123456)
        self.assertEqual(str(m), "12.35 USD")

    def test_rounding(self):
        m1 = Money.from_currency("USD", "1.235", rounding=ROUND_HALF_UP)
        m2 = Money.from_currency("USD", "1.235", rounding=ROUND_DOWN)
        self.assertEqual(str(m1), "1.24 USD")
        self.assertEqual(str(m2), "1.23 USD")

    def test_serialize(self):
        m = Money.from_currency("USD", "12.34")
        d = m.serialize()
        self.assertEqual(d["value"], "12.34")
        self.assertEqual(d["currency_code"], "USD")

    def test_with_pydantic(self):
        from pydantic import BaseModel

        class TestModelWithMoney(BaseModel):
            amount: Money

        model = TestModelWithMoney(amount=Money.from_currency("USD", "12.34"))
        data_field = model.amount
        self.assertEqual(str(data_field), "12.34 USD")
        model_raw_data = TestModelWithMoney.model_validate_json(
            '{"amount": {"currency_code": "USD", "value": "12.34"}}'
        )
        self.assertEqual(str(model_raw_data.amount), "12.34 USD")

        to_json = model_raw_data.model_dump_json()
        self.assertEqual(to_json, '{"amount":{"value":"12.34","currency_code":"USD"}}')


if __name__ == "__main__":
    unittest.main()
