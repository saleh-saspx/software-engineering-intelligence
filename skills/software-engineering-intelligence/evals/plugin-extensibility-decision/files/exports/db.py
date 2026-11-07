"""Data access for exports."""
from datetime import date

ORDER_COLUMNS = [
    "order_no", "order_date", "customer_no", "customer_name", "vat_id", "sku", "product_name",
    "quantity", "unit_price", "net_amount", "vat_amount", "gross_amount", "currency", "delivery_note",
]

_SQL = """
    SELECT order_no, order_date, customer_no, customer_name, vat_id, sku, product_name,
           quantity, unit_price, net_amount, vat_amount, gross_amount, currency, delivery_note
      FROM order_lines_export_v
     WHERE tenant_id = %(tenant_id)s
       AND order_date BETWEEN %(date_from)s AND %(date_to)s
     ORDER BY order_no, line_no
"""


def fetch_order_lines(conn, tenant_id: int, date_from: date, date_to: date) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(_SQL, {"tenant_id": tenant_id, "date_from": date_from, "date_to": date_to})
        columns = [c.name for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
