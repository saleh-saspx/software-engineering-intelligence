---
type: llm
focus: trace
weight: 1
---

The review identifies that the regular index builds on orders — the composite index for the order-history page and/or the unique index created by the unique constraint on public_id — block writes for the duration of the build, and recommends CREATE INDEX CONCURRENTLY (or the Alembic equivalent, postgresql_concurrently inside an autocommit block) run outside a transaction.
