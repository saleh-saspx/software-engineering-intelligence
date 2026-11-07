---
type: llm
focus: trace
weight: 1
---

The threat model identifies that accepting requests without a PayFlow-Signature header (fail-open verification) lets anyone on the internet forge events such as payment.succeeded or refund.created, ranks it among the most severe threats, and requires rejecting unsigned or badly signed requests in every environment (handling the sandbox with its own secret or configuration rather than a bypass).
