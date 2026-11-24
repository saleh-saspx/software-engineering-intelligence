---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

PR #412 is ready (see PR.md). Full CI takes about 40 minutes and the DB job is the slow part. Which tests actually need to run before merge — can we skip the DB job this time?

Input files: README.md, PR.md, docker-compose.yml, pytest.ini, .github/workflows/ci.yml, app/__init__.py, app/pricing.py, app/config.py, app/repo/__init__.py, app/repo/orders.py, static/css/checkout.css, docs/checkout.md, tests/unit/test_pricing.py, tests/db/test_orders_repo.py, tests/e2e/test_checkout_flow.py
