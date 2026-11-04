from billing.invoices import compute_invoice


def test_single_line():
    inv = compute_invoice([{"sku": "A", "quantity": 2, "unit_price": 10.0}])
    assert inv["subtotal"] == 20.0
    assert inv["tax"] == 3.8
    assert inv["total"] == 23.8


def test_volume_discount_applies_above_threshold():
    inv = compute_invoice([{"sku": "A", "quantity": 100, "unit_price": 20.0}])
    assert inv["subtotal"] == 1900.0
