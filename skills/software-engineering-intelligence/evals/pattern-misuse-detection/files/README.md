# orders-service

Order placement for the web shop (TypeScript, Node 20, no framework).

- `src/server.ts` — wiring and HTTP server
- `src/http` — middleware pipeline (request log → auth → rate limit) and routes
- `src/orders` — order placement; side effects run as `OrderPlaced` listeners on the event bus
- `src/pricing` — totals, tax and promotions (marketing configures promotions in the admin UI)
- `src/notifications` — e-mail via SendGrid (we only send e-mail; SMS is not on the roadmap)
- `src/persistence` — repositories (in-memory store standing in for the database driver)
- `src/shipping` — shipping cost estimate for the cart page
- `src/config` — configuration

Scripts: `npm test` (node:test via tsx), `npm run typecheck`.
