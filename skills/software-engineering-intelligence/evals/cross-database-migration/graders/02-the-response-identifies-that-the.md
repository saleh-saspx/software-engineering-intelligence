---
type: llm
focus: trace
weight: 1
---

The response identifies that the users.email unique key relies on MySQL's case- and accent-insensitive collation (utf8mb4_0900_ai_ci), so in PostgreSQL uniqueness and lookups become case-sensitive; it recommends citext, a unique index on lower(email) or a case-insensitive (nondeterministic ICU) collation, in place before writes reopen on PostgreSQL, with lookups that match case-insensitively.
