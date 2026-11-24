---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Our architect says this schema "isn't normalised enough" and wants 3NF everywhere — including removing unit_price from order_lines because "price already lives in products". The team disagrees. Who's right, and what should we actually change?

Input files: docs/architect-notes.md, db/schema.sql
