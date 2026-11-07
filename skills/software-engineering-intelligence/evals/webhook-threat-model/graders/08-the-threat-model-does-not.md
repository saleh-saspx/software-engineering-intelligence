---
type: llm
focus: trace
weight: 1
---

The threat model does not treat the absence of user authentication (session, JWT, OAuth) or the disabled CSRF protection on the webhook route as weaknesses; if it discusses them, it explains that the signature is the authentication mechanism for webhooks and that CSRF does not apply without ambient browser credentials.
