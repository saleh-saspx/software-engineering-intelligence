---
type: llm
focus: trace
weight: 1
---

The response adds verification to the plan — row counts and checksums or sampled comparisons per table, a rehearsal on a copy, and a realistic rollback (switching DB_CONNECTION back loses writes made after the cut-over) — rather than accepting step 5 as is.
