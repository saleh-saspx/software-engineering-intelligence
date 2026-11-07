---
type: llm
focus: trace
weight: 1
---

Criterion: proportionality. The response does not recommend removing the NotificationSender interface even though it has a single production implementation: it recognises it as the seam to the external SendGrid API that the tests use through FakeNotificationSender.
