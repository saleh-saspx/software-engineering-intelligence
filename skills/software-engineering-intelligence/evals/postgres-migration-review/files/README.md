# orders-service

Order management API behind the storefront and the partner integrations (marketplaces and
3PL warehouses sync orders through `orders/partner_api.py`).

## Stack
- Python 3.12, SQLAlchemy 2.0, Alembic 1.13
- PostgreSQL 15 (managed): one primary, one read replica used by reporting

## Data
- `orders` is the hottest table: about 40 million rows, 25 GB with indexes, roughly 300
  inserts/updates per second at peak. It is never quiet: partner sync jobs run around the clock
  and some reporting queries on the primary take several minutes.

## Deploying
- Rolling deploys on Kubernetes. An init container runs `alembic upgrade head` against the
  primary; then new pods start while the old pods keep serving traffic until the rollout
  finishes (usually 10–15 minutes). Partner sync workers are updated last.
- Alembic uses the default environment (`migrations/env.py`): the whole upgrade runs in one
  transaction.
- Production deploys happen in the evening, but traffic then is still about 60 % of peak.
