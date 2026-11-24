---
type: llm
focus: trace
weight: 1
---

The response explains that transfer() locks the two accounts in argument order, so concurrent transfers in opposite directions (A→B and B→A) each hold one lock and wait for the other — a deadlock — and recommends locking in a consistent order (for example by account id, or one SELECT … FOR UPDATE ordered by id), plus automatic retry of the transaction on deadlock (40P01) or serialization failure.
