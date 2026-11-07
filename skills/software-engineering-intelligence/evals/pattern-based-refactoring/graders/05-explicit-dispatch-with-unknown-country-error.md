---
type: llm
focus: trace
weight: 1
---

Criterion: correctness. The if/elif chain is replaced by an explicit mapping from country to tax rule (for example a dict of functions or objects, or a match statement) that raises an error for an unsupported country, and calculate_tax keeps its signature so billing/invoice.py and other callers work unchanged.
