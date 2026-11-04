import sqlite3
from contextlib import contextmanager

DB_PATH = "billing.db"


@contextmanager
def connect(path: str = DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def usage_for_customer(conn, customer_id: int, month: str):
    return conn.execute(
        "SELECT sku, quantity, unit_price FROM usage WHERE customer_id = ? AND month = ?",
        (customer_id, month),
    ).fetchall()


def save_invoice(conn, customer_id: int, month: str, lines, subtotal, tax, total, issued_at):
    cur = conn.execute(
        "INSERT INTO invoices (customer_id, month, subtotal, tax, total, issued_at) VALUES (?, ?, ?, ?, ?, ?)",
        (customer_id, month, subtotal, tax, total, issued_at),
    )
    invoice_id = cur.lastrowid
    for line in lines:
        conn.execute(
            "INSERT INTO invoice_lines (invoice_id, sku, quantity, amount) VALUES (?, ?, ?, ?)",
            (invoice_id, line["sku"], line["quantity"], line["amount"]),
        )
    return invoice_id


def invoice_totals_for_month(conn, month: str):
    # Reads the denormalised totals directly — see docs/adr/0001-store-invoice-totals.md
    return conn.execute(
        "SELECT customer_id, total FROM invoices WHERE month = ? ORDER BY total DESC", (month,)
    ).fetchall()
