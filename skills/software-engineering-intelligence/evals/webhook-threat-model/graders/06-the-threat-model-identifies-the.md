---
type: llm
focus: trace
weight: 1
---

The threat model identifies the server-side download of receipt_url as a server-side request forgery risk, made worse by the unauthenticated internal services and the reachable cloud metadata endpoint, and requires an allow-list of PayFlow's hosts or fetching the receipt through PayFlow's API instead.
