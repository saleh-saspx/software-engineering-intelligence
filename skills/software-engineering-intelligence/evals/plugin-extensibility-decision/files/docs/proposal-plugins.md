# Proposal: customer export plugins

Author: tech lead · Status: proposed

## Problem
Every new export format costs us one to three days, and enterprise customers keep asking for
more (`export-requests.md`). Product wants customers to be able to add formats themselves.

## Proposal
- Customers write a Python class implementing `ExportPlugin.render(rows: list[dict]) -> bytes` and
  upload the file in the admin.
- We store the file in S3 and, when the customer runs an export, load it with `importlib` inside
  the web process and call `render()` with the rows we have already fetched.
- Plugins only receive their own tenant's rows, so they cannot see other customers' data.
- No versioning needed: `rows` is simply our internal export row format (`ORDER_COLUMNS` in
  `exports/db.py`).
- If a plugin breaks, the customer fixes it.

## Effort
About two weeks, including the upload screen.
