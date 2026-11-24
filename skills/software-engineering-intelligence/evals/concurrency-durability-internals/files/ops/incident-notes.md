- Daily: ERROR: deadlock detected (SQLSTATE 40P01) in transfer(); clients retry manually.
- postings table 3x larger than expected after the monthly report runs; autovacuum runs but
  "dead row versions cannot be removed yet".
- Proposal: move ledger to RocksDB ("LSM = faster writes, no vacuum").
