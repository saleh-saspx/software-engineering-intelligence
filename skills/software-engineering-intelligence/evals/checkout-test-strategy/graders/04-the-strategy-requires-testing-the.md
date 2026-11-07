---
type: llm
focus: trace
weight: 1
---

The strategy requires testing the payment integration at its HTTP boundary — against a fake server, the provider's sandbox or contract tests — including timeout and retry behaviour, and requires an idempotency key (or equivalent) with a test showing that a retried charge does not charge twice.
