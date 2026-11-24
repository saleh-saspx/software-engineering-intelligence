from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def line_total(unit_price: Decimal, quantity: int, discount_rate: Decimal) -> Decimal:
    gross = unit_price * quantity
    return (gross - gross * discount_rate).quantize(CENT, rounding=ROUND_HALF_UP)


def order_total(lines) -> Decimal:
    return sum((line_total(l.unit_price, l.quantity, l.discount_rate) for l in lines), Decimal("0.00"))
