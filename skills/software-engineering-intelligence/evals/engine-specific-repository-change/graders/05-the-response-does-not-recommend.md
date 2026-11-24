---
type: llm
focus: trace
weight: 1
---

The response does not recommend replacing the Oracle-specific SQL with something chosen only because it passes on H2 (portable rewrites that are correct on Oracle, such as COALESCE or an IS NULL query, are fine), and does not suggest moving production off Oracle or adopting H2/SQLite as the reference engine to make testing easier.
