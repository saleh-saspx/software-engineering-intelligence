Review notes (architect):
1. order_lines.unit_price duplicates products.price → remove, join to products.
2. orders.customer_email duplicates customers.email → remove.
3. Addresses must be fully normalised: street → city → region → country tables.
4. product_attributes is flexible, keep it for all product data.
5. products.tags is fine, it's just text.
