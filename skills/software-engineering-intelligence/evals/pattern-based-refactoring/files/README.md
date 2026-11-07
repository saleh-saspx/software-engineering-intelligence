# billing

Invoice tax calculation for the shop's EU, US and Canadian customers. Finance reconciles the
`tax` amounts produced here against the ledger every month, so results must not change without
an explicit, reviewed decision.

- `billing/models.py` — customer, line and invoice value objects (money is `Decimal`)
- `billing/tax.py` — `calculate_tax(invoice)`
- `billing/invoice.py` — `invoice_total(invoice)`
- `docs/tax-rules.md` — the rules as agreed with our tax advisor

Run the tests with `python -m pytest`.
