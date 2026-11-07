---
type: llm
focus: trace
weight: 1
---

Criterion: correctness. The response identifies ConfigManager as a classic singleton holding mutable global state — read from business code such as PricingService and the notification factory, changed at runtime through POST /admin/config, and reset between tests — and recommends configuration that is read once at startup and passed to the objects that need it.
