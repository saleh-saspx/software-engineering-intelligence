# core-accounts

Retail banking accounts, transfers and FX for a single bank. PostgreSQL 16. Account numbers are
13 digits and may start with 0; branch codes are 4 digits (e.g. 0042); national IDs are 10 digits
with leading zeros; phone numbers include the country code. Rates from the central bank have up to
8 decimal places (e.g. 0.00002381 per unit for some currency pairs).
