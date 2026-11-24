---
type: llm
focus: trace
weight: 1
---

The response says order_lines.unit_price must stay: it records the price at the time of sale (a different fact from the current catalogue price), and removing it would change historical orders, invoices and refunds whenever products.price changes.
