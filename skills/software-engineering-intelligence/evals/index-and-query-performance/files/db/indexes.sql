CREATE INDEX orders_created_customer_idx ON orders (created_at, customer_id);
CREATE UNIQUE INDEX customers_email_idx ON customers (email);
CREATE INDEX orders_status_idx ON orders (status);
