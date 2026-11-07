# Design: PayFlow payment webhooks (draft v2)

Status: draft for review · Owner: payments squad

## Goal
Replace the 5-minute polling job with webhooks from PayFlow, so orders are marked paid within
seconds and refunds show up immediately. Keep the polling job switched off once webhooks work.

## Events we subscribe to
| Event | Payload (`data`) |
|---|---|
| `payment.succeeded` | `payment_id`, `order_id` (our order id, sent as metadata at checkout), `amount`, `currency`, `customer_email` |
| `payment.failed` | `payment_id`, `order_id`, `failure_reason` |
| `refund.created` | `refund_id`, `payment_id`, `order_id`, `amount`, `receipt_url` |

Every event also has `id` (unique per event), `type` and `created` (Unix time).

## Endpoint
`POST /webhooks/payflow/<merchant_id>` — each merchant pastes this URL into their PayFlow dashboard.

- It is a public endpoint: PayFlow cannot log in, so there is no session or API token. CSRF
  protection is switched off for this route because it is not a browser form.
- TLS terminates at the load balancer, as for the rest of the platform.

## Verifying requests
1. Load the merchant's signing secret from `merchant_payment_accounts` using the `merchant_id`
   in the URL.
2. If the `PayFlow-Signature` header is present, compute HMAC-SHA256 over the JSON body and
   compare it with the header. We parse the body and re-serialise it with sorted keys before
   hashing so whitespace differences don't matter.
3. If the header is missing we accept the request anyway: PayFlow's sandbox does not sign test
   events, and we want the same code path in every environment.

## Processing (synchronous, inside the request)
1. Parse the event and load the order: `Order.query.get(event["data"]["order_id"])`.
2. `payment.succeeded`: set `status = "paid"` and `paid_amount = data.amount`; call the fulfilment
   service to reserve stock and create the shipment (2–8 s); send the confirmation email.
3. `payment.failed`: set `status = "payment_failed"`.
4. `refund.created`: insert a `refunds` row with `data.amount`; set `status = "refunded"` when the
   refunds reach `paid_amount`; download the receipt PDF from `data.receipt_url` and attach it to
   the refund email.
5. Return 200. On any exception return 500, so PayFlow retries.

PayFlow behaviour: it retries any non-2xx response, and any response slower than 10 seconds, up
to 8 times over 24 hours, with the same event `id`. Events can arrive out of order.

## Observability
Log the full request (headers and body) at INFO level so we can debug the rollout.

## Testing
Manual testing with PayFlow's sandbox and its "send test event" button.

## Open questions
- Keep the polling job as a fallback?
