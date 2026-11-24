---
type: llm
focus: trace
weight: 1
---

The response explains that synchronous_commit = off can lose the most recently committed transactions on a crash (clients were told they committed) but does not corrupt the database (unlike fsync = off), and that for a ledger this is usually unacceptable unless the business explicitly accepts that loss; it recommends reverting or limiting it to non-critical transactions.
