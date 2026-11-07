# PR #873 · Warehouse fulfilment tracking and public order ids

- `migrations/versions/0042_orders_fulfilment.py`: adds `fulfilment_status`, `gift_note`,
  `public_id` and `warehouse_id` (with a foreign key), an index for the order-history page,
  renames `legacy_ref` to `external_ref`, and backfills `fulfilment_status` for shipped orders.
- `orders/models.py`: the new columns; `legacy_ref` renamed to `external_ref`.
- `orders/sync.py`: the partner sync worker matches on `external_ref` and sets
  `fulfilment_status`.

Tested locally with `alembic upgrade head` on a dev database with 5,000 orders: the upgrade takes
under a second, and downgrade works.

Plan: merge this afternoon and ship with tonight's normal rolling deploy.
