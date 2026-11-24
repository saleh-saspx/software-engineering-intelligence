---
type: llm
focus: trace
weight: 1
---

The response explains that LIKE '%term%' with a leading wildcard cannot use a B-tree index and offers a trigram (pg_trgm GIN/GiST) index or full-text search as alternatives.
