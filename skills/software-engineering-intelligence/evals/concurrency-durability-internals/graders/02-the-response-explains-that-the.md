---
type: llm
focus: trace
weight: 1
---

The response explains that the three-hour REPEATABLE READ transaction holds an old snapshot, so vacuum cannot remove row versions that are dead to everyone else ('cannot be removed yet'), which causes the bloat; it recommends a replica, shorter transactions or batches, or an export/snapshot instead of one long transaction.
