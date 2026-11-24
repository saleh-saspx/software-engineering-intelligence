---
type: llm
focus: trace
weight: 1
---

The response explains that Oracle treats the empty string as NULL, so storing '' for a missing middle name stores NULL and `middle_name = ''` matches no rows on Oracle — the findWithoutMiddleName test passes on H2 but the query is wrong in production (it should test `IS NULL`, or the model must change).
