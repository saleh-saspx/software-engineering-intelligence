# shipquote

HTTP service that returns shipping quotes for the checkout page.

- `cmd/shipquote` — main: configuration and wiring, HTTP server
- `internal/shipping` — quoting service, shipment model, packing-slip formatting
- `internal/ups` — client for the UPS rating API

`go test ./...` runs the tests (the UPS API is stubbed with httptest).
