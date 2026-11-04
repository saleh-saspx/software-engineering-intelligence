from datetime import datetime

TAX_RATE = 0.19
VOLUME_DISCOUNT_THRESHOLD = 1000
VOLUME_DISCOUNT = 0.05


def line_amount(quantity, unit_price):
    return quantity * unit_price


def compute_invoice(usage_rows):
    """Turn usage rows into invoice lines and totals."""
    lines = []
    subtotal = 0.0
    for row in usage_rows:
        amount = line_amount(row["quantity"], row["unit_price"])
        lines.append({"sku": row["sku"], "quantity": row["quantity"], "amount": amount})
        subtotal += amount
    if subtotal > VOLUME_DISCOUNT_THRESHOLD:
        subtotal = subtotal * (1 - VOLUME_DISCOUNT)
    tax = round(subtotal * TAX_RATE, 2)
    total = round(subtotal + tax, 2)
    return {"lines": lines, "subtotal": round(subtotal, 2), "tax": tax, "total": total}


def issue_invoice(conn, customer_id, month, db):
    rows = db.usage_for_customer(conn, customer_id, month)
    if not rows:
        return None
    inv = compute_invoice(rows)
    issued_at = datetime.utcnow().isoformat()
    invoice_id = db.save_invoice(conn, customer_id, month, inv["lines"], inv["subtotal"],
                                 inv["tax"], inv["total"], issued_at)
    return {"id": invoice_id, **inv, "issued_at": issued_at}
