# Checkout incidents, Q3 2026

## INC-311 · VAT one or two cents too high on multi-unit lines (July)
Customers buying three or more units of cheap items were charged slightly more VAT than the
invoice PDF showed. Cause: VAT was rounded per unit and then multiplied. Fixed in PR #412
(VAT is now rounded per line). No test was added: "covered by the existing pricing tests".

## INC-327 · Double charges after provider timeouts (August)
When the provider took longer than 5 seconds, `PaymentClient.charge` retried. The first attempt
had in fact succeeded, so 41 customers were charged twice; support refunded them by hand.
Proposed fix: send an idempotency key with each charge — not implemented yet.

## INC-340 · Exclusive partner coupon stacked with the newsletter coupon (September)
The partner's exclusive 40 % coupon could be combined with the 10 % newsletter coupon when it was
entered second. The test covering this had been skipped in June as "flaky" and was never switched
back on. Fixed in PR #455.

## INC-352 · Checkout down for 40 minutes after release 2026.38 (September)
A configuration change renamed the provider URL environment variable. The unit tests passed (the
provider is mocked) and the e2e suite was off; customers reported it.
