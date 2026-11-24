# orders-service

Python 3.12 · FastAPI · PostgreSQL 16 (production and staging).

Tests:
- `pytest -m "not db and not e2e"` — unit tests, ~40 s
- `pytest -m db` — repository tests against PostgreSQL 16 started by docker compose, ~9 min
- `pytest -m e2e` — browser checkout flow against a deployed preview, ~25 min
