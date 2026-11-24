---
type: llm
focus: trace
weight: 1
---

The response notes that after loading data with explicit ids, PostgreSQL sequences/identity columns must be reset to the maximum id, or new inserts will collide.
