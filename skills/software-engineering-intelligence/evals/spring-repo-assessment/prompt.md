---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

We're about to start subscription billing next quarter on this backend. Can you assess the repo's architecture and technical debt and give me a prioritized tech debt backlog? It's a git repo, so feel free to look at the history.

Input files: pom.xml, README.md, src/main/resources/application.properties, src/main/java/com/acme/shop/ShopApplication.java, src/main/java/com/acme/shop/orders/Order.java, src/main/java/com/acme/shop/orders/OrderLine.java, src/main/java/com/acme/shop/orders/OrderRepository.java, src/main/java/com/acme/shop/orders/OrderController.java, src/main/java/com/acme/shop/orders/OrderService.java, src/main/java/com/acme/shop/billing/BillingClient.java, src/main/java/com/acme/shop/billing/InvoiceCalculator.java, src/main/java/com/acme/shop/reporting/LegacyReportGenerator.java, src/test/java/com/acme/shop/orders/OrderServiceTest.java
