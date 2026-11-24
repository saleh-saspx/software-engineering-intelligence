---
type: llm
focus: trace
weight: 1
---

The response says card_expires_at must not be a MySQL TIMESTAMP: TIMESTAMP's range ends on 2038-01-19 and values are converted through the session time zone, so a DATE (expiry is a calendar date) or a DATETIME holding UTC is needed.
