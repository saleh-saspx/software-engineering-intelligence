# Source registry and provenance conventions

Read this when you need to justify a recommendation, answer "where does this rule come from?",
or decide how much weight a rule deserves. Rules cite sources with the IDs below.

## Contents
1. Corpus sources (S1–S8)
2. External references (X1–X23)
3. Provenance labels
4. Citation format
5. Coverage gaps
6. Copyright and licensing

## 1. Corpus sources

These are the documents supplied with the skill. Every `S` citation in the rule catalog was
checked against the text of these documents; chapter and section names are the documents' own.

| ID | Source | Coverage available | Licence noted in document |
|----|--------|--------------------|---------------------------|
| S1 | Robert C. Martin et al., *Clean Code: A Handbook of Agile Software Craftsmanship*, Prentice Hall, 2008/2009 | Full book (Ch.1–17, appendices). Ch.17 "Smells and Heuristics" codes (C1–C5, E1–E2, F1–F4, G1–G36, J1–J3, N1–N7, T1–T9) are cited as `S1 G5` etc. | All rights reserved (Pearson) |
| S2 | Robert C. Martin, *Clean Architecture: A Craftsman's Guide to Software Structure and Design*, Prentice Hall, 2017 | Full book (Ch.1–34, incl. Ch.34 "The Missing Chapter" by Simon Brown, Appendix A) | All rights reserved (Pearson) |
| S3 | Philippe Kruchten, Robert Nord, Ipek Ozkaya, *Managing Technical Debt: Reducing Friction in Software Development*, Addison-Wesley, 2019 (ISBN 9780135645932) — **publisher sample** | Front matter, preface, **Chapter 1 only**, and the index. Principles 1–9 are cited by their statement as listed in Ch.1; their full treatment (Ch.2–13) is **not** in the corpus. | All rights reserved (Pearson) |
| S4 | Darius Kunce, Dominik Goby, *AWS Prescriptive Guidance — Using architectural decision records to streamline decision-making during development*, AWS, 2022 | Full (18 pp.) | AWS documentation |
| S5 | Larry Conklin, Gary Robinson (leads), *OWASP Code Review Guide v2.0*, OWASP, 2017 | Full (220 pp.). Organised around the OWASP Top 10 **2013** numbering (A1 Injection … A10 Unvalidated Redirects). Focus languages: Java, C#/.NET, some C/C++ and PHP. | Creative Commons Attribution (per cover) |
| S6 | OWASP, *Web Security Testing Guide v4.2*, 2020 | Full (465 pp.). Test IDs such as `WSTG-INPV-05` are cited directly. | Creative Commons 4.0 (per §1 Frontispiece) |
| S7 | Anders Møller, Michael I. Schwartzbach, *Static Program Analysis*, Aarhus University, lecture notes dated 15 Oct 2026 | Full (Ch.1–12) | CC BY-NC-ND 4.0 |
| S8 | Thomas Hastings, *Software Engineering: Standing on the Shoulders of Giants*, First Edition 1.0b16, 2026 — open textbook at swebook.org, following the ACM/IEEE SE2014 curriculum (SEEK). **Not** the IEEE SWEBOK Guide, despite the domain name. | Chapters used: 3 (User Requirements — fit criteria, traceability, attack trees, STRIDE), 6 (Design and Architecture), 7 (Architectural Patterns), 9 (Static Checking), 10 (Testing), 11 (Software Security), 12 (Quality Metrics), 13 (Software Engineering in the Age of AI), 14 (Delivery: CI/CD, DevOps, and Operations), 15 (Maintenance and Evolution). Cited by section number, e.g. `S8 §10.1.5`. Checked against the online chapters retrieved on 2026-11-07, at the level of section headings and stated claims; the book is a beta edition, so section numbers may move. | CC BY-SA 4.0 for text and figures; MIT for code examples |

### WSTG identifier map (S6)
WSTG section numbers map one-to-one to test IDs: §4.1.n → `INFO-n`, §4.2.n → `CONF-n`,
§4.3.n → `IDNT-n`, §4.4.n → `ATHN-n`, §4.5.n → `ATHZ-n`, §4.6.n → `SESS-n`, §4.7.n → `INPV-n`,
§4.8.n → `ERRH-n`, §4.9.n → `CRYP-n`, §4.10.n → `BUSL-n`, §4.11.n → `CLNT-n`, §4.12.1 → `APIT-01`.
Examples: `WSTG-INPV-05` SQL injection, `WSTG-ATHZ-04` insecure direct object references,
`WSTG-INPV-19` server-side request forgery, `WSTG-SESS-05` CSRF. Tests added in later WSTG
editions (for example CSV/formula injection) are not in S6: cite them as X14 and name the edition.

### OWASP Top 10 numbering caution (S5, S8)
S5 uses 2013 category numbers; S8 §11.2 uses **OWASP Top 10:2025** (A01 Broken Access Control,
A02 Security Misconfiguration, A03 Software Supply Chain Failures, A04 Cryptographic Failures, A05
Injection, A06 Insecure Design, A07 Authentication Failures, A08 Software or Data Integrity
Failures, A09 Security Logging and Alerting Failures, A10 Mishandling of Exceptional Conditions).
Cite categories **by concept**, and map to whichever edition the user's organisation uses; the
2025 → rule map is in `workflows/security-review.md` §11.

## 2. External references (not in the corpus)

These are cited only to attribute widely known concepts that the corpus does not cover. They
were **not** checked against their text in this environment: cite them by title, chapter or item
name, never by page, and never quote them. Prefer an `S` source whenever one supports the point.

| ID | Reference | Used for |
|----|-----------|----------|
| X1 | Eric Evans, *Domain-Driven Design*, 2003 | Bounded contexts, ubiquitous language, aggregates |
| X2 | Gamma, Helm, Johnson, Vlissides, *Design Patterns*, 1994 | Pattern vocabulary |
| X3 | Martin Fowler, *Refactoring* (2nd ed.), 2018 | Named refactorings, small behaviour-preserving steps |
| X4 | Michael Feathers, *Working Effectively with Legacy Code*, 2004 | Characterization tests, seams |
| X5 | Mike Cohn, *Succeeding with Agile*, 2009 | Test pyramid |
| X6 | Michael Nygard, *Release It!* | Timeouts, circuit breakers, bulkheads |
| X7 | The Twelve-Factor App (12factor.net) | Config in environment, build/release/run separation, stateless processes |
| X8 | Semantic Versioning specification (semver.org) | Versioning public contracts |
| X9 | Adam Tornhill, *Your Code as a Crime Scene* | Hotspots = change frequency × complexity |
| X10 | OWASP Application Security Verification Standard (ASVS) | Verification levels for security requirements |
| X11 | Official ecosystem guides: Effective Go and Go Code Review Comments; PEP 8 / PEP 20; PHP-FIG PSR-12 and Laravel docs; Spring docs; TypeScript handbook; React docs (Rules of Hooks); Oracle/Google Java style; PostgreSQL and MySQL reference manuals; Django, Rails and Alembic migration docs | Language and engine conventions (see `languages/`) |
| X12 | Donald Knuth, "Structured Programming with go to Statements", 1974 | Premature optimisation caution |
| X13 | Pat Helland / general distributed-systems practice | Idempotency, at-least-once delivery, outbox |
| X14 | Common industry practice (no single source) | Engineering recommendations labelled `extension` |
| X15 | Joshua Bloch, *Effective Java*, 2nd ed., 2008 | API design and extensibility (Items 13, 15–18, 38–40, 43–44), exceptions (Items 60–65), concurrency (Items 66–70), serialization as a public API (Items 74–78), exact arithmetic (Item 48), optimisation (Item 55). Item numbers are the 2nd edition's; the 3rd edition (2017) renumbers them (e.g. Item 17 → 19, Item 70 → 82). |
| X16 | Eric Freeman, Elisabeth Robson, Kathy Sierra, Bert Bates, *Head First Design Patterns*, 2004 | OO design principles (encapsulate what varies, program to interfaces, favour composition, open–closed, depend on abstractions, least knowledge, Hollywood principle) and the intent of Strategy, Observer, Decorator, Factory, Adapter/Facade, Template Method, State, Proxy |
| X17 | Brian Goetz et al., *Java Concurrency in Practice*, 2006 | Thread safety and publication (Ch.2–3), composing and documenting thread-safe classes (Ch.4), liveness hazards (Ch.10), performance and scalability, Amdahl's law, lock contention (Ch.11), testing concurrent programs (Ch.12) |
| X18 | Doug Lea, *Concurrent Programming in Java: Design Principles and Patterns*, 2nd ed., 1999 | Safety, liveness, performance and reusability as competing design forces; immutability and confinement (Ch.2) |
| X19 | Scott Oaks, *Java Performance: The Definitive Guide*, 2014 | Performance-testing method — micro/meso/macro benchmarks, warm-up, variability (Ch.2); database access performance — statements, pools, transactions, result-set handling, JPA (Ch.11) |
| X20 | Michael T. Minella, *Pro Spring Batch*, 2011 | Chunk-oriented processing, job state and restartability (Ch.5–6), skip/retry, scaling and partitioning (Ch.11), testing batch processes (Ch.12) |
| X21 | Cormen, Leiserson, Rivest, Stein, *Introduction to Algorithms*, 3rd ed., 2009 | Loop invariants as correctness arguments (Ch.2), growth of functions (Ch.3), B-trees as the structure behind most database indexes (Ch.18) |
| X22 | OWASP Top 10 for LLM Applications, 2025 edition (check for newer editions) | Prompt injection, sensitive information disclosure, improper output handling, excessive agency, system prompt leakage, unbounded consumption |
| X23 | Jerome Saltzer, Michael Schroeder, "The Protection of Information in Computer Systems", 1975 | Secure design principles: economy of mechanism, fail-safe defaults, complete mediation, open design, separation of privilege, least privilege, least common mechanism, psychological acceptability |

X15–X21 were selected from the reading list supplied for version 1.1 because they bear on the
focus areas of that release (architecture, data, verification, extensibility, security). The other
titles on that list (interview preparation, language tutorials, finance) were not used.

## 3. Provenance labels

Every rule and principle carries one label:

- **direct** — the cited `S` source states the point (in its own words; the skill paraphrases).
- **synthesized** — the skill combines several sources, or resolves a tension between them, into
  a position no single source states. The rule names each contributing source.
- **extension** — an engineering recommendation beyond the corpus (cites `X` refs or none).
  Weigh these as expert judgement, not as sourced fact.
- **convention** — an ecosystem or project convention (language guide, framework docs, team
  rules). Local convention outranks generic guidance unless safety is at stake.

When explaining a finding to a user, say which kind it is if it matters to the decision
("Clean Code recommends…", "this is common practice, not from the reference books…").

## 4. Citation format

`S1 Ch.3 (Do One Thing)` · `S1 G30` · `S2 Ch.14 (ADP)` · `S3 Ch.1, Principle 5` ·
`S5 A4 Insecure Direct Object Reference` · `S6 WSTG-ATHZ-04` · `S7 §1.2` · `S8 §10.1.5` ·
`X15 Item 17` · `X17 Ch.11` · `X3`.

## 5. Coverage gaps

The corpus is strong on code-level craft (S1), architecture and dependency management (S2, S8
Ch.6–7), web application security review and testing (S5, S6), security across the lifecycle and
the software supply chain (S8 Ch.11), testing theory — selection, adequacy, oracles, mutation,
coverage criteria (S8 Ch.10), delivery and release safety (S8 Ch.14), measurement (S8 Ch.12) and
the limits of analysis (S7). It is thin or silent on:

- **Domain-Driven Design, design patterns catalogue, refactoring catalogue, legacy-code
  techniques** → extension rules citing X1–X4, X16; S8 Ch.15 covers characterization tests,
  refactoring under green tests and the strangler fig.
- **Database design and operations** (isolation levels, migrations on live systems, replication,
  backups, batch processing) → mostly `extension`, anchored where possible in S8 §7.2.1 (shared
  data), §14.1.6 (CAP), §14.3.2–14.3.4 (schema compatibility, irreversible migrations) and §14.4.3
  (system of record vs. cache), plus X19–X20 and the engine manuals (X11).
- **Performance engineering and capacity** → X17 Ch.11, X19 Ch.2, S8 §14.1.2 (horizontal scaling);
  claims stay labelled measured or unmeasured.
- **Technical debt beyond Chapter 1** → S3 sample gives the definition, principal/interest, and
  the nine principles' statements; S8 §15.5 adds deliberate vs. inadvertent debt; prioritisation
  mechanics in this skill are `synthesized`.
- **Language specifics** → S5 covers Java/.NET and some PHP for security; X15/X17 cover Java
  API design and concurrency; everything else is `convention` from official ecosystem guides (X11).
- **Formal methods, observability (SLOs, tracing), incident response, infrastructure as code** →
  not covered by S8 either; `extension` only.
- **Non-web security** (embedded, mobile, cloud IAM) and **LLM-specific threats** → S8 Ch.13 covers
  verification of AI output but not prompt injection; X22 attributes LLM risks; recommend specialist
  review for embedded, mobile and cloud IAM.

## 6. Copyright and licensing

S1–S3 are copyrighted books, as are X15–X21. This skill contains only short paraphrases,
structural references (chapter, item and heuristic names), and original synthesis — no reproduced
passages. Keep it that way when extending the skill: paraphrase, cite the section, never paste
text. S5/S6 (Creative Commons), S7 (CC BY-NC-ND) and S8 (CC BY-SA 4.0 text, MIT code) are likewise
referenced, not redistributed; reusing S8's *text* (rather than its ideas) would carry CC BY-SA
obligations — attribution and share-alike. Distribute source documents separately and only as
their licences allow; do not link to unlicensed copies.
