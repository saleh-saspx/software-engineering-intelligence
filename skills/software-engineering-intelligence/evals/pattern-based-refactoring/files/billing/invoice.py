from decimal import Decimal

from .tax import calculate_tax


def invoice_total(invoice):
    subtotal = sum((line.amount for line in invoice.lines), Decimal("0"))
    tax = calculate_tax(invoice)
    return {"subtotal": subtotal, "tax": tax, "total": subtotal + tax}
