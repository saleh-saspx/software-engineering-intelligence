---
type: llm
focus: trace
weight: 1
---

The review identifies that renaming legacy_ref to external_ref breaks the old pods and the partner sync workers that keep running the previous code during the rolling deploy, and recommends an expand/contract sequence (add the new column, dual-write or sync, switch reads, drop later) or keeping the database column name and mapping it to the new attribute name in the ORM.
