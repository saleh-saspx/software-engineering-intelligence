---
type: llm
focus: trace
weight: 1
---

parse_age raises ValueError for negative input such as "-1", still returns 42 for " 42 ", and still raises ValueError for "200".
