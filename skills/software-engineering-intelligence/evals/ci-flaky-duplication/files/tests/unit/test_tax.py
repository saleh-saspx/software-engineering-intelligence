from decimal import Decimal

from shop.tax import vat


def test_vat_rounding():
    assert vat(Decimal("10.05")) == Decimal("2.01")


def test_zero_rated():
    assert vat(Decimal("10.00"), zero_rated=True) == Decimal("0.00")
