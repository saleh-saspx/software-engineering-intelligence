---
type: llm
focus: trace
weight: 1
---

The review identifies that the SKU is inserted into the supplier URL without escaping (e.g. it should use url.Values / url.QueryEscape).
