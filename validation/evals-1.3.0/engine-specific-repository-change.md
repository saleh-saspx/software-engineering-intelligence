Verdict: blocked. Production runs Oracle but CI runs on H2, and one of the new queries can't work on Oracle.

Findings (most severe first):

- [blocker · confirmed] `CustomerRepository.java:32` — `findWithoutMiddleName` never matches anything on Oracle. Oracle stores `''` as NULL, and `middle_name = ''` is then a comparison with NULL, which is never true. The test passes only because H2 keeps `''` as a real value. Fix: make NULL the only meaning of "no middle name", turn blank input into `null`, and use:
  ```java
  @Query("select c from Customer c where c.middleName is null")
  List<Customer> findWithoutMiddleName();
  ```
  This follows from Oracle's documented `''`-as-NULL rule; I couldn't run it here (DATA-TYPE-05).

- [major · confirmed] `application-test.properties:1` — The 48 green tests say nothing about Oracle. They ran on H2 against a schema Hibernate generated (`create-drop`), not your real one. Nothing shows MERGE … FROM dual, ROWNUM or NVL ever running on Oracle. Of the tests you sent, only the two in `CustomerRepositoryTest` touch this code. Fix: before merging, run those tests and the new ones below on Oracle at your production version. Use Testcontainers or a throwaway schema on a shared Oracle test database, with `@AutoConfigureTestDatabase(replace = Replace.NONE)`. Tag the tests so CI keeps running them. H2's Oracle mode isn't enough, because it imitates only parts of Oracle (TEST-DATA-02).

- [major · likely] `CustomerRepository.java:26` — No test calls `findPageForBranch`, and `ORDER BY full_name` isn't unique. Tied rows have no defined order, so customers with the same name can appear twice or go missing across pages. Fix: `ORDER BY full_name, id`, and test it on Oracle with tied names across a page boundary. Nothing measured backs "JPQL was slow", so compare `DBMS_XPLAN.DISPLAY_CURSOR` plans before you keep Oracle-only SQL.

- [major · confirmed] `CustomerRepositoryTest.java:19` — The test only counts rows, so it still passes if `WHEN MATCHED` updates nothing. Assert that the name became "Sara Radmehr", and add a negative case to the middle-name test (TEST-ORACLE-01).

- [major · possible] `CustomerRepository.java:11` — `@Modifying` queries need an existing transaction. `save()` opened its own, but this method doesn't, and `@DataJpaTest`'s per-test transaction hides that. Add `@Transactional` unless every caller already has one. I didn't see the callers or check this against your Spring Data version.

- [minor · likely] `CustomerRepository.java:13` — MERGE isn't race-free. Two concurrent upserts of a new national ID can both take the insert branch, and one gets ORA-00001 (`DataIntegrityViolationException`). The race isn't new, and deduplication depends on the `national_id` unique index existing in production. H2 builds that index from the entity, so CI never checked it. Confirm the index exists and retry once on that exception (REL-CONS-03).

- [nit] Use `COALESCE` instead of `NVL` on line 35 so it stays portable.

Question: the MERGE insert never sets `branch_code`, so customers it creates never appear in `findPageForBranch`. Is that intended?

Scope: I read all eight files in full, as they are now (no git history, so no diff). I didn't see the callers, the other 45 tests, the CI config, the production DDL or the Oracle version.
Checks run: no tests. This machine has no Oracle, H2, Docker daemon, network or Maven cache. The `pom.xml` you sent has no versions, so Maven rejects it. Static checks: `repo_survey.py` and `test_impact.py` (both flag Oracle in production and H2 in tests), plus `test_smells.py` and `security_scan.py` (no leads). Reading the code, every value is a bound parameter. "48 tests, all green" comes from the PR; I didn't see that run.

## Trace

Shell commands, in order (`S` = `/home/claude/work/repo/skills/software-engineering-intelligence`):

1. `ls -la S/ S/references/ S/scripts/ S/assets/` — listed the skill layout.
2. `mkdir -p /tmp/eval-oracle && cd /tmp/eval-oracle && bash S/evals/engine-specific-repository-change/place-files.sh && find /tmp/eval-oracle -type f | sort` — placed the 8 fixture files.
3. `ls -la` of reference and template folders.
4. `rules.py --help; rules.py show TEST-DATA-02 DATA-TYPE-05 DATA-PORT-01 TEST-REPORT-01` — printed the usage and the 4 rules.
5. `grep`/`awk` over references/data/types.md and performance.md — headings, types.md §7 (NULL/empty; Oracle stores `''` as NULL), pagination lines.
6. performance.md §8 and §13; `rules.py show API-PAGE-01 TEST-ORACLE-01 TEST-DATA-01`.
7. knowledge-model.md section list and §4.4 confidence table.
8. `command -v` for java, javac, mvn, gradle, docker, podman, sqlplus, h2; `test_impact.py --help` — java, javac, mvn, gradle and docker binaries exist; podman, sqlplus and h2 not found.
9. `java -version; docker info; ls ~/.m2/repository; find` for jars — OpenJDK 21.0.12; docker daemon not running; no H2, Oracle JDBC or HSQLDB jar.
10. `docker version …; mvn -o validate` with a scratch repo — Docker daemon unreachable; Maven offline validate exited 1 (4 missing dependency versions); scratch removed.
11. `repo_survey.py /tmp/eval-oracle` — Java/Spring Boot; Oracle in app config and driver, H2 in test config, with a warning that H2 tests are not evidence for Oracle.
12. `test_impact.py /tmp/eval-oracle --files src/main/java/com/acme/crm/CustomerRepository.java` — data-access change with Oracle-specific SQL (NVL, ROWNUM). Required: CustomerRepositoryTest and database tests on Oracle. Recommended: the full suite.
13. `test_smells.py /tmp/eval-oracle` — 2 files, 3 tests analysed, no smell matched.
14. `security_scan.py … --files CustomerRepository.java` — 0 hits.
15. `rules.py show REL-CONS-03; rules.py search "tie"; rules.py search "deterministic"`.
16. `check_report.py --help`.
17–20. `check_report.py --light` on drafts — draft 1: 2 errors (`[question]` not a valid label) and 727 words against ~450; draft 2: 614 words; draft 3: 544 words; after 3 wording edits: 0 errors, 559 words (kept for the data-semantics content).
21. Removed the scratch draft; only the 8 fixture files remain.

Skill files read: in full — SKILL.md; references/workflows/code-review.md, database-review.md, test-strategy.md; references/testing/database-matrix.md, selection.md; references/data/engines.md; references/languages/java-spring.md, sql.md; assets/templates/review-report.md. Excerpts — references/data/types.md, performance.md, knowledge-model.md. Rules: TEST-DATA-02, DATA-TYPE-05, DATA-PORT-01, TEST-REPORT-01, API-PAGE-01, TEST-ORACLE-01, TEST-DATA-01, REL-CONS-03.
