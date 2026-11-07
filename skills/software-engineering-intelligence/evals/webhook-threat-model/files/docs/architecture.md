# Architecture overview

```
customers ──HTTPS──▶ load balancer ──▶ web (Flask) ──▶ PostgreSQL (all merchants, merchant_id on every row)
merchant staff ─────▶ (TLS ends here)  │            ──▶ Redis (sessions, cache, Celery broker)
                                       │
                                       ├──▶ fulfilment service (internal HTTP, no auth inside the VPC)
                                       └──▶ email provider (API)
Celery workers ──▶ PostgreSQL, PayFlow API (polling job), email provider
```

- The web tier and the workers run in the same VPC as the internal services. The cloud metadata
  endpoint is reachable from every instance (no IMDS hop limit configured).
- Merchant PayFlow credentials: API key and webhook signing secret per merchant, stored encrypted
  in the `merchant_payment_accounts` table. Our own PayFlow account (used to bill merchants for
  their subscription) has its signing secret in `config/webhooks.yaml`, committed to the
  repository so every environment has the same value.
- Orders: `orders(id, merchant_id, status, total_amount, currency, paid_amount, ...)`. Order ids are
  sequential integers.
- Logs from every service go to the shared log platform: retention one year, readable by all
  engineers and the support team.
