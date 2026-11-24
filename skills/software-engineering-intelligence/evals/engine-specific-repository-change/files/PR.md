# PR #77 — customer dedup and paging

- `CustomerRepository.upsertByNationalId` now uses a native MERGE statement instead of find-then-save.
- `findPageForBranch` uses a native query with ROWNUM paging (the JPQL version was slow).
- Customers without a middle name are now stored with an empty string; `findWithoutMiddleName`
  looks for `middle_name = ''`.
CI: 48 tests, all green.
