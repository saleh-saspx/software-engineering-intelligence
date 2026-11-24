CREATE TABLE customers (
  id            bigserial PRIMARY KEY,
  national_id   integer NOT NULL UNIQUE,
  full_name     varchar(200) NOT NULL,
  phone         bigint,
  postal_code   integer,
  birth_date    timestamp
);

CREATE TABLE accounts (
  id              bigserial PRIMARY KEY,
  account_number  bigint NOT NULL UNIQUE,
  branch_code     smallint NOT NULL,
  currency        char(3) NOT NULL,
  balance         double precision NOT NULL DEFAULT 0,
  status          varchar(20) NOT NULL,
  holders         jsonb NOT NULL,          -- [{"customer_id": 12, "role": "owner"}, ...]
  opened_at       timestamp NOT NULL DEFAULT now()
);

CREATE TABLE transactions (
  id            bigserial PRIMARY KEY,
  account_id    bigint NOT NULL REFERENCES accounts(id),
  reference     integer NOT NULL,
  amount        real NOT NULL,
  value_date    timestamp NOT NULL,
  created_at    timestamp NOT NULL DEFAULT now()
);

CREATE TABLE fx_rates (
  id           bigserial PRIMARY KEY,
  pair         varchar(7) NOT NULL,          -- 'USD/EUR'
  rate         numeric(10,4) NOT NULL,
  fetched_at   timestamp NOT NULL
);

CREATE TABLE loans (
  id             bigserial PRIMARY KEY,
  account_id     bigint NOT NULL REFERENCES accounts(id),
  principal      numeric NOT NULL,
  interest_rate  numeric(5,2) NOT NULL       -- 4.75
);
