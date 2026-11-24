---
type: llm
focus: trace
weight: 1
---

The response explains that the index (created_at, customer_id) has the columns in the wrong order for `customer_id = ? AND created_at >= ?` ordered by created_at, so PostgreSQL walks the 90-day range of all customers' orders until the page is filled, and recommends an index on (customer_id, created_at) — equality column first, range/order column second.
