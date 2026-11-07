---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

we're shipping PR #873 tonight with the normal rolling deploy, so migration 0042 runs on prod. orders is ~40M rows on postgres 15. anything I should worry about before I hit go?

Input files: README.md, PR.md, alembic.ini, requirements.txt, migrations/env.py, migrations/versions/0041_orders_baseline.py, migrations/versions/0042_orders_fulfilment.py, orders/__init__.py, orders/models.py, orders/sync.py
