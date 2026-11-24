---
type: llm
focus: trace
weight: 1
---

The response says the account holders list stored in JSONB should be a relationship table (account_holders with foreign keys to accounts and customers and a role column), because JSON cannot enforce referential integrity or be joined and constrained per holder.
