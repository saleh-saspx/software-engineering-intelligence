---
type: llm
focus: trace
weight: 1
---

The response recommends against loading customer-uploaded Python code in the web process, explaining that it is remote code execution with the process's privileges — the database connection and credentials, every tenant's data, secrets and network access — so the proposal's claim that plugins only see their own tenant's rows does not hold.
