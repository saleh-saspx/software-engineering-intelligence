---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Product wants enterprise customers to be able to add their own export formats. Our lead's proposal is in docs/proposal-plugins.md — customers upload Python plugins that we load at runtime. Is that the right call? The export code is in exports/, and docs/export-requests.md lists what customers actually asked for.

Input files: README.md, requirements.txt, pytest.ini, docs/proposal-plugins.md, docs/export-requests.md, exports/__init__.py, exports/db.py, exports/service.py, exports/sap_idoc.py, tests/test_exports.py
