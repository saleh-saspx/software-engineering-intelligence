from decimal import Decimal

from app.pricing import line_total


def test_line_total_without_discount():
    assert line_total(Decimal("10.00"), 2, Decimal("0")) == Decimal("20.00")
