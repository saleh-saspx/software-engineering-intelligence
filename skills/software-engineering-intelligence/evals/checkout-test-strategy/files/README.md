# shop-checkout

Checkout for our web shop: cart pricing with VAT per destination country, coupons, card payment
through the payment provider's REST API, and order creation.

- Python 3.12. The provider is called over HTTPS through `checkout/payment.py` and
  `checkout/http_transport.py`.
- Team of four developers. We release every Thursday; rollback means redeploying the previous image.
- CI runs the unit tests with a coverage gate of 90 % (last run: 91 %). The browser end-to-end suite
  in `tests/e2e/` has been switched off in CI since August — it was flaky and took about 25 minutes.
- Next quarter we rebuild checkout to add multi-currency (EUR, GBP, CHF) and saved cards.

Last quarter's incidents are in `docs/incidents.md`.
