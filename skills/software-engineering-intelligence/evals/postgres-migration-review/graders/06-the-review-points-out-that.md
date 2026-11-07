---
type: llm
focus: trace
weight: 1
---

The review points out that the whole upgrade runs in one transaction, so the strongest lock taken early is held until commit while the later steps run, and/or that no lock_timeout is set, so the ALTER TABLE can queue behind long-running queries and block all traffic to orders while it waits.
