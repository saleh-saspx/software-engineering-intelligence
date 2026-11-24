---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

We're moving our Laravel app from MySQL 8 to PostgreSQL 16 next quarter. Plan is in docs/migration-plan.md — pgloader for the data, and to keep CI fast we'd run the test suite on SQLite in memory. Does the plan hold up?

Input files: docs/migration-plan.md, database/schema-mysql.sql, app/Repositories/StockRepository.php, phpunit.xml, .env.example
