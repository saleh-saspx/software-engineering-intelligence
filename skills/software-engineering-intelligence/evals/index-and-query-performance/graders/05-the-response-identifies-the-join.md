---
type: llm
focus: trace
weight: 1
---

The response identifies the join `c.id::text = o.legacy_customer_ref` as a type mismatch (a cast on the join key) that prevents using the index on customers.id, and recommends joining on columns of the same type (a proper bigint foreign key, or casting the other side with care).
