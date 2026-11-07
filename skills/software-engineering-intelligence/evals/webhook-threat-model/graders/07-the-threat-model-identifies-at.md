---
type: llm
focus: trace
weight: 1
---

The threat model identifies at least two of these weaknesses: logging full request headers and bodies (signatures and customer personal data in one-year logs readable by support), the platform signing secret committed in config/webhooks.yaml, and computing the HMAC over re-serialised JSON instead of the raw request body with a constant-time comparison.
