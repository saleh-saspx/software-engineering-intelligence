# shop-orders

Spring Boot 3 service for order placement (Java 21, PostgreSQL via JdbcTemplate).

## Business rules
- An order is accepted only if its stock has been reserved — we never charge for items we
  cannot ship.
- Compliance: every order attempt gets an audit row in `order_audit`, and that row must be kept
  even if placing the order fails afterwards (for example, the payment is declined).
- Each merchant uses one payment provider (Stripe or Adyen), configured in `merchants`.

## Layout
- `order` — REST API, order placement, persistence
- `inventory` — stock reservation
- `payment` — payment providers
- `pricing` — discounts and multi-currency price display
- `fx` — exchange rates (ECB)
- `shipping` — shipping quotes through ParcelNet (vendored client in `shipping.parcelnet`)
- `notify` — confirmation e-mails
- `storage` — object storage for archived confirmations
- `audit` — audit log file
- `web` — servlet filters
