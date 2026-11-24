---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Our ledger service (PostgreSQL 16) has deadlocks every day and the tables keep bloating. One engineer wants to move the ledger to a RocksDB-based store because "LSM trees are faster for writes". Another already turned synchronous_commit off to speed things up. What's actually going on?

Input files: README.md, ledger/transfer.py, jobs/monthly_report.py, ops/postgresql.conf, ops/incident-notes.md
