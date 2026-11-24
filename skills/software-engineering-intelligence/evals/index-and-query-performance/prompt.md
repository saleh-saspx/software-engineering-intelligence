---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

The customer orders page got slow (p95 ~4 s) since we passed 20M orders. Code, indexes and the EXPLAIN we captured are attached. What should we fix first?

Input files: README.md, db/indexes.sql, orders/views.py, orders/queries.py, docs/explain-orders-page.txt
