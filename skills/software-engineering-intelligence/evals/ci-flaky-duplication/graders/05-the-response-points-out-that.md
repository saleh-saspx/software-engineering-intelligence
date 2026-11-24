---
type: llm
focus: trace
weight: 1
---

The response points out that test_locking never runs on PostgreSQL in this setup (the skip condition compares against 'postgres' while the matrix value is 'postgres:16', or it is skipped in both runs), so locking behaviour is currently unverified.
