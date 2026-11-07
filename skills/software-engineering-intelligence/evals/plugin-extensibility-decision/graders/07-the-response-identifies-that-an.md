---
type: llm
focus: trace
weight: 1
---

The response identifies that an export loads all of a tenant's order lines into memory and builds the whole file inside the web request (a problem for the tenant with 2.1 million lines a year), and recommends streaming or chunked generation, for example as a background job.
