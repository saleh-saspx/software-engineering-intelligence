---
type: llm
focus: trace
weight: 1
---

The response points out that InnoDB created indexes for the foreign-key columns automatically (e.g. orders.user_id) but PostgreSQL does not, so the FK columns need explicit indexes after the move.
