# PR #412 — checkout fixes

Changed files:
- `app/pricing.py` — line totals now rounded half-up to cents per line instead of on the order total
- `app/repo/orders.py` — order sync uses an upsert keyed on `external_id` instead of select-then-insert
- `app/config.py` — new flag `SPLIT_PAYMENTS_ENABLED` (default off)
- `static/css/checkout.css` — button spacing
- `docs/checkout.md` — describes the new rounding

Author note: "only small changes, the DB job is slow, can we merge on unit tests?"
