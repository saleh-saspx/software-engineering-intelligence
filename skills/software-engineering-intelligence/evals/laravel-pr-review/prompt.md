---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Can you review PR #214 before I merge it? The description is in PR.md; the changed files are the OrderController, the Order model, the order show view, routes/web.php and the new migration. It's a Laravel 11 app.

Input files: PR.md, composer.json, .env.example, routes/web.php, app/Models/Order.php, app/Http/Controllers/OrderController.php, resources/views/orders/show.blade.php, database/migrations/2026_10_01_000000_add_notes_to_orders_table.php
