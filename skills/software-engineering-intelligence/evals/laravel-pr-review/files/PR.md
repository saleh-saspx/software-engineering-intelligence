# PR #214: Order search, CSV export and editable order notes

Adds three things requested by the support team:
- `GET /orders/search?status=…&sort=…` — search a customer's orders by status
- `GET /orders/export` — CSV export of all orders for the monthly report
- `PUT /orders/{id}` — customers can edit their order (delivery notes, address)

Notes are shown on the order page so support can read them.
