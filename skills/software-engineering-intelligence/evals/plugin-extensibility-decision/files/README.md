# wholesale-portal

B2B ordering portal for food wholesalers. Each wholesaler is a tenant; their business customers
(bakeries, restaurants, shops) order through it.

- Python 3.12, Flask, PostgreSQL (one shared database, `tenant_id` on every row), Celery for
  background jobs.
- About 140 tenants; the largest has 2.1 million order lines a year. Three backend developers.
- SOC 2 Type II audited. Several enterprise contracts require that no other party can access the
  tenant's data.
- Exports: tenant staff download their order lines for a date range from the admin, in one of six
  formats (`exports/`). The export runs inside the web request.
