---
type: llm
focus: trace
weight: 1
---

The response explains that changing amount from DECIMAL(10,2) to DECIMAL(19,4) changes the column's type definition, which MySQL 8.0 performs by copying/rebuilding the table (not as an INSTANT or metadata-only change), so on 80M rows it runs for a long time while blocking writes to payments, and replicas fall behind while they replay it.
