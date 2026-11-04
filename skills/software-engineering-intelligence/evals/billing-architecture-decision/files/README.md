# billing

Internal invoicing tool for the finance team (2 developers). Flask app + SQLite.
Generates monthly invoices from usage records and exposes a small JSON API used by the
finance dashboard.

Run: `pip install -r requirements.txt && flask --app billing.app run`
Test: `pytest`
