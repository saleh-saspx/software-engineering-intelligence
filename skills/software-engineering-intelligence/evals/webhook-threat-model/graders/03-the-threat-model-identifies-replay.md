---
type: llm
focus: trace
weight: 1
---

The threat model identifies replay of captured events (no timestamp or freshness check) and/or the missing idempotency on the event id, and requires deduplicating events by id (for example with a unique constraint) so that retries and replays cannot ship, refund or email twice.
