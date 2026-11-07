from datetime import date
from decimal import Decimal

import pytest

from exports import service as export_service
from exports.service import ExportService

ROWS = [
    {
        "order_no": "SO-1001", "order_date": date(2026, 10, 1), "customer_no": "C-17",
        "customer_name": "Bäckerei Krüger", "vat_id": "DE123456789", "sku": "FLOUR-25",
        "product_name": "Wheat flour type 550, 25 kg", "quantity": 4, "unit_price": Decimal("18.40"),
        "net_amount": Decimal("73.60"), "vat_amount": Decimal("5.15"), "gross_amount": Decimal("78.75"),
        "currency": "EUR", "delivery_note": "Ring twice",
    },
]
OCTOBER = (date(2026, 10, 1), date(2026, 10, 31))


@pytest.fixture(autouse=True)
def fake_rows(monkeypatch):
    monkeypatch.setattr(export_service, "fetch_order_lines", lambda conn, tenant, start, end: [dict(r) for r in ROWS])


def test_csv_has_header_and_rows():
    lines = ExportService(conn=None).export(1, "csv", *OCTOBER).decode().strip().splitlines()
    assert lines[0].startswith("order_no,order_date,customer_no")
    assert lines[1].startswith("SO-1001,2026-10-01,C-17")


def test_semicolon_csv_uses_decimal_commas():
    out = ExportService(conn=None).export(1, "csv_semicolon", *OCTOBER).decode()
    assert "SO-1001;2026-10-01" in out
    assert ";18,40;" in out


def test_sap_idoc_has_one_idoc_per_order():
    out = ExportService(conn=None).export(1, "sap_idoc", *OCTOBER)
    assert out.count(b"<IDOC") == 1
    assert b"<BELNR>SO-1001</BELNR>" in out


def test_unknown_format_is_rejected():
    with pytest.raises(ValueError):
        ExportService(conn=None).export(1, "pdf", *OCTOBER)
