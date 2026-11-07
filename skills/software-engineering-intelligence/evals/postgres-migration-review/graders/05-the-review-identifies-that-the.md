---
type: llm
focus: trace
weight: 1
---

The review identifies that the backfill UPDATE of all shipped orders inside the migration is dangerous on this table (one long transaction touching millions of rows: row locks, bloat, WAL and replica lag, and holding the migration's locks until it finishes), and recommends a separate batched, restartable backfill job run after the deploy.
