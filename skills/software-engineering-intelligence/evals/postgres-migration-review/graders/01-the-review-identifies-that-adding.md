---
type: llm
focus: trace
weight: 1
---

The review identifies that adding public_id with a gen_random_uuid() default rewrites the whole orders table under an ACCESS EXCLUSIVE lock (a volatile default cannot use PostgreSQL's fast default), blocking reads and writes for the duration, and proposes adding the column without the volatile default (nullable, default only for new rows), backfilling in batches, and enforcing NOT NULL and uniqueness afterwards in a non-blocking way.
