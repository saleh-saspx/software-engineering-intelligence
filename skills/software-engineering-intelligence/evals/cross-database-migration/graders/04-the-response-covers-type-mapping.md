---
type: llm
focus: trace
weight: 1
---

The response covers type mapping by meaning: tinyint(1) to boolean (and the code paths comparing with 0/1), and zero dates '0000-00-00' that PostgreSQL rejects and must be cleaned or turned into NULL; unsigned bigint has no direct PostgreSQL equivalent.
