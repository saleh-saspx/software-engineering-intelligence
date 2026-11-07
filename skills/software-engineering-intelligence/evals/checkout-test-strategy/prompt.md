---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

We're rebuilding checkout next quarter (multi-currency + saved cards) and honestly our tests don't catch anything — see docs/incidents.md. Can you look at the current suite and propose a test strategy for the rebuild?

Input files: README.md, requirements-dev.txt, pytest.ini, .coveragerc, .github/workflows/ci.yml, docs/incidents.md, checkout/__init__.py, checkout/pricing.py, checkout/coupons.py, checkout/payment.py, checkout/http_transport.py, checkout/service.py, tests/test_pricing.py, tests/test_coupons.py, tests/test_checkout_service.py, tests/e2e/test_checkout_ui.py
