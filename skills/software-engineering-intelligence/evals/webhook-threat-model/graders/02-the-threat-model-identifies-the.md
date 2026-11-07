---
type: llm
focus: trace
weight: 1
---

The threat model identifies the cross-tenant risk: the signing secret is chosen by the merchant_id in the URL, but the order is loaded globally by the order_id in the payload, so a merchant who controls their own PayFlow account and secret could mark paid or refund another merchant's orders; it requires scoping the order lookup to that merchant (and checking that the payment belongs to that merchant's PayFlow account).
