---
tags: [software-engineering-intelligence]
max_turns: 50
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

We need to add DHL rates next to UPS — requirements are in docs/requirements.md. Sam proposed a carrier framework in docs/proposal-carriers.md. Which design should we build? Show me the shape of the code (types, interfaces, wiring), not the full implementation.

Input files: README.md, go.mod, docs/requirements.md, docs/proposal-carriers.md, cmd/shipquote/main.go, internal/shipping/shipment.go, internal/shipping/quote.go, internal/shipping/packingslip.go, internal/shipping/quote_test.go, internal/ups/client.go
