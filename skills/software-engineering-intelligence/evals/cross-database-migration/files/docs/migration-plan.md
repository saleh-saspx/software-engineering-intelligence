# MySQL 8 → PostgreSQL 16

1. Freeze writes for 2 hours, run pgloader from MySQL to PostgreSQL.
2. Switch DB_CONNECTION to pgsql.
3. Eloquent abstracts the database, so application code should work unchanged.
4. CI: run phpunit on SQLite in memory (fast, no services).
5. Roll back by switching DB_CONNECTION back if something breaks.
