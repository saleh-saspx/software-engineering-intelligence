---
type: llm
focus: trace
weight: 1
---

The response requires running the repository tests (MERGE upsert, ROWNUM paging, NVL, empty-string behaviour) against a real Oracle before merge — for example a Testcontainers Oracle image (such as gvenzl/oracle-free) or a shared Oracle test schema — and treats this as required, not optional.
