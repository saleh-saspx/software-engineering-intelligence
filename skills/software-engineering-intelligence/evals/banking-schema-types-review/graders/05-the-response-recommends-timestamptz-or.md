---
type: llm
focus: trace
weight: 1
---

The response recommends timestamptz (or a documented UTC convention) for event times such as created_at, opened_at and fetched_at, and date (not timestamp) for business dates such as value_date and birth_date, explaining what goes wrong across time zones or midnight.
