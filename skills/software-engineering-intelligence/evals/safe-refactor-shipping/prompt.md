---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Please refactor calculate_shipping in shipping/rates.py — nobody can read it anymore. Behaviour must stay exactly the same: checkout uses it and so does an import job in another repo (same signature). Do whatever you need to make it safe.

Input files: README.md, shipping/__init__.py, shipping/rates.py, shipping/checkout.py
