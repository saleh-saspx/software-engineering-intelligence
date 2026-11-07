---
type: llm
focus: trace
weight: 1
---

The threat model identifies that synchronous processing (the 2–8 second fulfilment call plus emails and downloads) can exceed PayFlow's 10-second limit and trigger retries and duplicate side effects, and recommends acknowledging quickly and processing asynchronously (queue or outbox, e.g. the existing Celery workers) with idempotent handlers.
