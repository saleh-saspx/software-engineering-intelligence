from decimal import Decimal

import pytest

from checkout.pricing import Line, cart_totals, line_total, vat_for_line, vat_rate


@pytest.mark.parametrize(
    ("country", "rate"),
    [("DE", "0.19"), ("FR", "0.20"), ("NL", "0.21"), ("IT", "0.22"), ("AT", "0.20")],
)
def test_vat_rate_by_country(country, rate):
    assert vat_rate(country) == Decimal(rate)


def test_unknown_country_is_rejected():
    with pytest.raises(ValueError):
        vat_rate("XX")


def test_line_total_three_units():
    expected = line_total(Decimal("19.99"), 1) * 3
    assert line_total(Decimal("19.99"), 3) == expected


def test_vat_for_line():
    net = Decimal("33.33")
    assert vat_for_line(net, "DE") == (net * vat_rate("DE")).quantize(Decimal("0.01"))


def test_cart_totals():
    lines = [Line(Decimal("9.99"), 2), Line(Decimal("0.35"), 7)]
    cart_totals(lines, "DE")


def test_gross_is_net_plus_vat():
    totals = cart_totals([Line(Decimal("10.00"), 1)], "FR")
    assert totals["gross"] == totals["net"] + totals["vat"]
