CREATE TABLE customers (id bigint PRIMARY KEY, email varchar(254) NOT NULL UNIQUE, name varchar(200) NOT NULL);

CREATE TABLE countries (id int PRIMARY KEY, name varchar(100) NOT NULL);
CREATE TABLE regions (id int PRIMARY KEY, country_id int NOT NULL REFERENCES countries(id), name varchar(100) NOT NULL);
CREATE TABLE cities (id int PRIMARY KEY, region_id int NOT NULL REFERENCES regions(id), name varchar(100) NOT NULL);
CREATE TABLE streets (id int PRIMARY KEY, city_id int NOT NULL REFERENCES cities(id), name varchar(200) NOT NULL);
CREATE TABLE addresses (id bigint PRIMARY KEY, street_id int NOT NULL REFERENCES streets(id), house_number varchar(20), postcode varchar(20));

CREATE TABLE products (
  id     bigint PRIMARY KEY,
  sku    varchar(40) NOT NULL UNIQUE,
  name   varchar(200) NOT NULL,
  price  numeric(12,2) NOT NULL,
  tags   text                       -- 'summer,sale,kids'
);

CREATE TABLE product_attributes (
  product_id bigint NOT NULL REFERENCES products(id),
  attr_name  varchar(50) NOT NULL,   -- 'weight_kg', 'colour', 'voltage', ...
  attr_value varchar(200),
  PRIMARY KEY (product_id, attr_name)
);

CREATE TABLE orders (
  id              bigint PRIMARY KEY,
  customer_id     bigint NOT NULL REFERENCES customers(id),
  customer_email  varchar(254) NOT NULL,
  shipping_address_id bigint NOT NULL REFERENCES addresses(id),
  placed_at       timestamptz NOT NULL
);

CREATE TABLE order_lines (
  order_id    bigint NOT NULL REFERENCES orders(id),
  line_no     int NOT NULL,
  product_id  bigint NOT NULL REFERENCES products(id),
  quantity    int NOT NULL CHECK (quantity > 0),
  unit_price  numeric(12,2) NOT NULL,
  PRIMARY KEY (order_id, line_no)
);
