---
type: llm
focus: trace
weight: 1
---

Criterion: correctness. The response identifies the Strategy pattern in payments — PaymentService as the context, the PaymentProvider interface, and the Stripe and Adyen providers as concrete strategies injected by Spring as a Map keyed by bean name and selected from the merchant's configuration — and judges it appropriate, noting that an unknown provider fails with an exception rather than silently.
