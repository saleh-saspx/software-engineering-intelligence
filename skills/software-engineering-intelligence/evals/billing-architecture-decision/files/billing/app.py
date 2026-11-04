from flask import Flask, jsonify, request

from billing import db, invoices

app = Flask(__name__)


@app.post("/invoices")
def create_invoice():
    payload = request.get_json(force=True)
    customer_id = int(payload["customer_id"])
    month = payload["month"]
    with db.connect() as conn:
        invoice = invoices.issue_invoice(conn, customer_id, month, db)
    if invoice is None:
        return jsonify({"error": "no usage for that month"}), 404
    return jsonify(invoice), 201


@app.get("/reports/monthly/<month>")
def monthly_report(month):
    with db.connect() as conn:
        rows = db.invoice_totals_for_month(conn, month)
    return jsonify([{"customer_id": r["customer_id"], "total": r["total"]} for r in rows])
