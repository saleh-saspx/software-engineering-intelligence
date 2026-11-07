---
tags: [software-engineering-intelligence]
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Our orders service has picked up a lot of design patterns and new people find it hard to follow. Review how patterns are used in src/: which ones earn their keep, which are misapplied, and what you would change first. Don't rewrite anything yet — I want a prioritised assessment we can plan from.

Input files: README.md, docs/CHANGELOG.md, package.json, src/config/ConfigManager.ts, src/events/EventBus.ts, src/http/middleware.ts, src/http/pipeline.ts, src/notifications/NotificationSender.ts, src/notifications/NotificationSenderFactory.ts, src/notifications/SendGridEmailSender.ts, src/orders/OrderService.ts, src/orders/listeners.ts, src/orders/types.ts, src/payments/PaymentClient.ts, src/persistence/AuditedRepository.ts, src/persistence/BaseRepository.ts, src/persistence/CachedRepository.ts, src/persistence/OrderRepository.ts, src/pricing/DiscountStrategy.ts, src/pricing/PricingService.ts, src/server.ts, src/shipping/ShippingCostVisitor.ts, test/orders.test.ts, test/pricing.test.ts, test/support/fakes.ts, tsconfig.json
