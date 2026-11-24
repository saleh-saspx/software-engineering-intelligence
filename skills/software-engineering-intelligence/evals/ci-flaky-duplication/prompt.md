---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Our CI takes ~45 minutes and keeps going red randomly, but the summary always ends up saying 100% pass after reruns. Can you cut the time without losing coverage, and tell me whether that 100% is real? Last two runs' JUnit files are in reports/.

Input files: README.md, .github/workflows/ci.yml, scripts/summary.sh, pytest.ini, reports/run-1041.xml, reports/run-1042.xml, tests/unit/test_cart.py, tests/unit/test_tax.py, tests/db/test_orders.py
