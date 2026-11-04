---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Our tech lead wants to restructure the billing service into hexagonal architecture — ports and adapters, repository interfaces, use-case classes, DTOs between layers. It's the small Flask app in this folder (internal tool for finance, 2 devs, we ship maybe one feature a quarter). Is that refactor worth it? Review the code and give me a recommendation, plus anything else important you spot.

Input files: README.md, requirements.txt, billing/__init__.py, billing/app.py, billing/db.py, billing/invoices.py, docs/adr/0001-store-invoice-totals.md, tests/test_invoices.py
