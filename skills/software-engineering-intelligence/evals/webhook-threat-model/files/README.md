# storefront-platform

Multi-tenant e-commerce platform: merchants run their shops on it, and their customers buy
through them. About 2,300 merchants, 9 engineers.

- Python 3.12, Flask, PostgreSQL 15, Redis, Celery workers (already used for emails and reports)
- Every row that belongs to a merchant carries `merchant_id`. Merchant staff sign in to the admin
  with sessions; the storefront uses customer sessions.
- Payments: each merchant connects their **own** PayFlow account (our payment provider) in the
  admin. Today a job polls PayFlow every 5 minutes for every merchant to find paid and refunded
  orders. Merchants complain that orders stay "pending" for minutes and that confirmation emails
  are slow.

See `docs/architecture.md` for the components and `docs/webhook-design.md` for the proposed change.
