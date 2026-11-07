---
tags: [software-engineering-intelligence]
max_turns: 70
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Every new country means another elif in billing/tax.py, and we broke VAT twice this year (see CHANGELOG.md). Please refactor the tax calculation so that adding a country is safe. Keep the results identical — finance reconciles these numbers every month.

Input files: README.md, pytest.ini, requirements-dev.txt, CHANGELOG.md, docs/tax-rules.md, billing/__init__.py, billing/models.py, billing/invoice.py, billing/tax.py, tests/__init__.py, tests/test_tax.py
