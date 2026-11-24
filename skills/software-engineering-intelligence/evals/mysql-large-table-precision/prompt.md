---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Can we run this migration on Friday night? MySQL 8.0, payments has ~80M rows, two read replicas used by the reporting app. It's the new migration in database/migrations.

Input files: README.md, config/database.php, database/migrations/2026_11_20_000000_widen_payment_amounts.php, app/Models/Payment.php
