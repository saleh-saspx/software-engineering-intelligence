---
type: llm
focus: trace
weight: 1
---

The response rejects running CI on SQLite for a PostgreSQL target (SQLite would not catch PostgreSQL behaviour, and the raw SQL here is not even portable) and recommends running the suite — at least the data-access tests — on PostgreSQL 16, and on MySQL as well while both are in use or during the transition.
