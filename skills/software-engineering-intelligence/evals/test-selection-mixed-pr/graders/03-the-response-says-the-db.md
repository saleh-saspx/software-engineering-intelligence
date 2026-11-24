---
type: llm
focus: trace
weight: 1
---

The response says the DB job (or database tests for the upsert) must not be skipped: the upsert's behaviour depends on PostgreSQL (ON CONFLICT … DO UPDATE … RETURNING against the unique index it relies on, now(), the driver's parameter style), so it needs tests against PostgreSQL itself, including the update-on-conflict path — not mocks, not SQLite, not an in-memory stand-in.
