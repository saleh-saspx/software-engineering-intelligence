---
type: llm
focus: trace
weight: 1
---

The response recommends storing account_number, national_id, phone, postal_code and branch_code (and the transaction reference) as strings (varchar/char/text) with format checks rather than integer types, explaining that leading zeros, '+' prefixes, letters or lengths are lost or not validated in numeric types; it cites the README's leading-zero facts or equivalent.
