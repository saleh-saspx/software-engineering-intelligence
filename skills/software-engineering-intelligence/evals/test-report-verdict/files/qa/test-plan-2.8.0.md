# Test plan — 2.8.0

Changes: refund flow rewritten (`billing/refunds.py`), new repository query for refund history
using PostgreSQL window functions, partner webhook payload gains `refund_reason`.

| Group | Class | Where | Engine |
|---|---|---|---|
| Refund unit tests (`tests/unit/billing`) | Required | PR | none |
| Refund repository tests (`tests/integration/refunds`) | Required | PR | PostgreSQL 16 |
| API tests (`tests/api`) | Required | PR | PostgreSQL 16 (shared) |
| Partner webhook contract tests (`tests/contract/partner`) | Required | main | — |
| Load test of refund history | Recommended | release | PostgreSQL 16, prod-sized copy |
