from decimal import Decimal

from billing.invoice import invoice_total
from billing.models import Customer, Invoice, Line
from billing.tax import calculate_tax


def test_german_consumer_pays_19_percent():
    invoice = Invoice(Customer("DE"), (Line("Desk", Decimal("100.00")),))
    assert calculate_tax(invoice) == Decimal("19.00")


def test_california_sales_tax():
    invoice = Invoice(Customer("US", region="CA"), (Line("Desk", Decimal("200.00")),), seller_country="US")
    assert calculate_tax(invoice) == Decimal("14.50")


def test_invoice_total_adds_tax():
    invoice = Invoice(Customer("DE"), (Line("Lamp", Decimal("10.00")),))
    assert invoice_total(invoice)["total"] == Decimal("11.90")
