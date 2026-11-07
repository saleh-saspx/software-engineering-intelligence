"""Cart pricing: line totals and VAT per destination country."""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
VAT_RATES = {
    "DE": Decimal("0.19"),
    "FR": Decimal("0.20"),
    "NL": Decimal("0.21"),
    "IT": Decimal("0.22"),
    "AT": Decimal("0.20"),
}


@dataclass(frozen=True)
class Line:
    unit_price: Decimal
    quantity: int


def vat_rate(country: str) -> Decimal:
    try:
        return VAT_RATES[country]
    except KeyError:
        raise ValueError(f"unsupported country: {country}") from None


def line_total(unit_price: Decimal, quantity: int) -> Decimal:
    if quantity < 1:
        raise ValueError("quantity must be at least 1")
    return (unit_price * quantity).quantize(CENT, ROUND_HALF_UP)


def vat_for_line(net: Decimal, country: str) -> Decimal:
    # INC-311: VAT is rounded per line, not per unit
    return (net * vat_rate(country)).quantize(CENT, ROUND_HALF_UP)


def cart_totals(lines: list[Line], country: str) -> dict[str, Decimal]:
    nets = [line_total(line.unit_price, line.quantity) for line in lines]
    net = sum(nets, Decimal("0.00"))
    vat = sum((vat_for_line(n, country) for n in nets), Decimal("0.00"))
    return {"net": net, "vat": vat, "gross": net + vat}
