# Migration plan: <schema or data change>

<!-- For schema or data changes on live systems (references/workflows/database-review.md §6;
     DATA-MIG-01..03, DATA-BACKUP-01). Each step must leave old and new application versions
     working against the schema. Never run destructive steps without a verified backup and
     explicit confirmation (AGT-SAFE-01). -->

## Change
- **Goal:** <what changes and why>
- **Engine and version:** <PostgreSQL 16 / MySQL 8.0.x / …>
- **Tables affected:** <name — row count — size — write rate at peak>
- **Deployment model:** <rolling / blue-green / canary; how long old and new code overlap>

## Risk assessment
| Operation | Lock taken / rewrite? | Measured duration on prod-sized copy | Blocks | Mitigation |
|---|---|---|---|---|
| <CREATE INDEX on orders(status)> | <SHARE lock; blocks writes> | <~6 min> | <writes> | <CREATE INDEX CONCURRENTLY outside a transaction> |

## Steps
<!-- Expand → migrate → contract. One release per line where code must change in between.
     Set lock_timeout (PostgreSQL) or ALGORITHM/LOCK (MySQL) on each DDL step. -->
| # | Release | Step | Old code OK? | New code OK? |
|---|---|---|---|---|
| 1 | R1 | <add nullable column `total_amount`> | yes | yes |
| 2 | R1 | <dual-write total and total_amount in application> | yes | yes |
| 3 | job | <batched, idempotent backfill (DATA-BATCH-01)> | yes | yes |
| 4 | R2 | <read from total_amount; stop writing total> | — | yes |
| 5 | R3 | <drop column total after the deprecation window> | — | yes |

## Verification
| Check | How | Result |
|---|---|---|
| Migrations apply from scratch and from previous release | <CI job> | <…> |
| Rehearsal on production-sized copy | <command, duration, locks observed> | <…> |
| Backfill idempotent and resumable | <re-run test> | <…> |
| Smoke tests of old and new app versions against intermediate schema | <…> | <…> |

## Rollback and roll-forward
- **Backup:** <type, time taken, restore verified? (DATA-BACKUP-01)>
- **Rollback possible until step:** <n> — **procedure:** <…>
- **Irreversible steps:** <which; roll-forward plan; who decides>
- **Abort criteria:** <lock wait > N s, error rate > X%, replication lag > Y s>
