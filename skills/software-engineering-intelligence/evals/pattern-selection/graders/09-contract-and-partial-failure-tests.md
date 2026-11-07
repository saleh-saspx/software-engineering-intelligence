---
type: llm
focus: trace
weight: 1
---

Criterion: correctness. The response plans tests that verify the design: the same contract tests run against every quoter implementation (for example table-driven tests against httptest servers) and a test that one carrier failing or timing out still yields the other carrier's quote.
