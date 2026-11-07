---
type: llm
focus: trace
weight: 1
---

Criterion: correctness. When the response discusses JdbcTemplate, it describes it as the template-callback style (the template runs the fixed JDBC steps and calls back into lambdas such as the row mapper and statement creator) and does not present it as the GoF Template Method implemented by subclassing; if JdbcTemplate is not discussed at all, this criterion fails.
