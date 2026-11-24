---
type: llm
focus: trace
weight: 1
---

The response explains that `lower(email) = lower(%s)` cannot use the plain unique index on email and recommends an expression index on lower(email) (or a case-insensitive type/collation, or normalising emails on write), and that `date(created_at) = %s` should be rewritten as a half-open range on created_at (created_at >= day AND created_at < day + 1 day) so an index on created_at can be used.
