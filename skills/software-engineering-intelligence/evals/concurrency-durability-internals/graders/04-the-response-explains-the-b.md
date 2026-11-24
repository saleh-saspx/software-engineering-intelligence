---
type: llm
focus: trace
weight: 1
---

The response explains the B-tree versus LSM-tree trade-off — LSM buffers writes and compacts later (write throughput, but read and space amplification and compaction cost) — and that switching the storage engine neither fixes the lock-ordering deadlock nor removes the need for transactions and invariants in a ledger.
