# Source registry and provenance conventions

Read this when you need to justify a recommendation, answer "where does this rule come from?",
or decide how much weight a rule deserves. Rules cite sources with the IDs below.

## Contents
1. Corpus sources (S1–S7)
2. External references (X1–X14)
3. Provenance labels
4. Citation format
5. Coverage gaps
6. Copyright and licensing

## 1. Corpus sources

These are the documents supplied with the skill. Every `S` citation in the rule catalog was
checked against the text of these files; chapter and section names are the documents' own.

| ID | Source | Coverage available | Licence noted in document |
|----|--------|--------------------|---------------------------|
| S1 | Robert C. Martin et al., *Clean Code: A Handbook of Agile Software Craftsmanship*, Prentice Hall, 2008/2009 | Full book (Ch.1–17, appendices). Ch.17 "Smells and Heuristics" codes (C1–C5, E1–E2, F1–F4, G1–G36, J1–J3, N1–N7, T1–T9) are cited as `S1 G5` etc. | All rights reserved (Pearson) |
| S2 | Robert C. Martin, *Clean Architecture: A Craftsman's Guide to Software Structure and Design*, Prentice Hall, 2017 | Full book (Ch.1–34, incl. Ch.34 "The Missing Chapter" by Simon Brown, Appendix A) | All rights reserved (Pearson) |
| S3 | Philippe Kruchten, Robert Nord, Ipek Ozkaya, *Managing Technical Debt: Reducing Friction in Software Development*, Addison-Wesley, 2019 (ISBN 9780135645932) — **publisher sample** | Front matter, preface, **Chapter 1 only**, and the index. Principles 1–9 are cited by their statement as listed in Ch.1; their full treatment (Ch.2–13) is **not** in the corpus. | All rights reserved (Pearson) |
| S4 | Darius Kunce, Dominik Goby, *AWS Prescriptive Guidance — Using architectural decision records to streamline decision-making during development*, AWS, 2022 | Full (18 pp.) | AWS documentation |
| S5 | Larry Conklin, Gary Robinson (leads), *OWASP Code Review Guide v2.0*, OWASP, 2017 | Full (220 pp.). Organised around the OWASP Top 10 **2013** numbering (A1 Injection … A10 Unvalidated Redirects). Focus languages: Java, C#/.NET, some C/C++ and PHP. | Creative Commons Attribution (per cover) |
| S6 | OWASP, *Web Security Testing Guide v4.2*, 2020 | Full (465 pp.). Test IDs such as `WSTG-INPV-05` are cited directly. | Creative Commons 4.0 (per §1 Frontispiece) |
| S7 | Anders Møller, Michael I. Schwartzbach, *Static Program Analysis*, Aarhus University, lecture notes dated 15 Oct 2026 | Full (Ch.1–12) | CC BY-NC-ND 4.0 |

### WSTG identifier map (S6)
WSTG section numbers map one-to-one to test IDs: §4.1.n → `INFO-n`, §4.2.n → `CONF-n`,
§4.3.n → `IDNT-n`, §4.4.n → `ATHN-n`, §4.5.n → `ATHZ-n`, §4.6.n → `SESS-n`, §4.7.n → `INPV-n`,
§4.8.n → `ERRH-n`, §4.9.n → `CRYP-n`, §4.10.n → `BUSL-n`, §4.11.n → `CLNT-n`, §4.12.1 → `APIT-01`.
Examples: `WSTG-INPV-05` SQL injection, `WSTG-ATHZ-04` insecure direct object references,
`WSTG-INPV-19` server-side request forgery, `WSTG-SESS-05` CSRF.

### OWASP Top 10 numbering caution (S5)
S5 uses 2013 category numbers. Later Top 10 editions merged and renamed categories (for
example, insecure direct object references and missing function-level access control were
later grouped under broken access control). Cite categories **by concept**, and map to
whichever edition the user's organisation uses.

## 2. External references (not in the corpus)

These are cited only to attribute widely known concepts that the corpus does not cover. They
were **not** checked against their text in this environment: cite them by title, never by page,
and never quote them. Prefer an `S` source whenever one supports the point.

| ID | Reference | Used for |
|----|-----------|----------|
| X1 | Eric Evans, *Domain-Driven Design*, 2003 | Bounded contexts, ubiquitous language, aggregates |
| X2 | Gamma, Helm, Johnson, Vlissides, *Design Patterns*, 1994 | Pattern vocabulary |
| X3 | Martin Fowler, *Refactoring* (2nd ed.), 2018 | Named refactorings, small behaviour-preserving steps |
| X4 | Michael Feathers, *Working Effectively with Legacy Code*, 2004 | Characterization tests, seams |
| X5 | Mike Cohn, *Succeeding with Agile*, 2009 | Test pyramid |
| X6 | Michael Nygard, *Release It!* | Timeouts, circuit breakers, bulkheads |
| X7 | The Twelve-Factor App (12factor.net) | Config in environment, build/release/run separation |
| X8 | Semantic Versioning specification (semver.org) | Versioning public contracts |
| X9 | Adam Tornhill, *Your Code as a Crime Scene* | Hotspots = change frequency × complexity |
| X10 | OWASP Application Security Verification Standard (ASVS) | Verification levels for security requirements |
| X11 | Official ecosystem guides: Effective Go and Go Code Review Comments; PEP 8 / PEP 20; PHP-FIG PSR-12 and Laravel docs; Spring docs; TypeScript handbook; React docs (Rules of Hooks); Oracle/Google Java style | Language conventions (see `languages/`) |
| X12 | Donald Knuth, "Structured Programming with go to Statements", 1974 | Premature optimisation caution |
| X13 | Pat Helland / general distributed-systems practice | Idempotency, at-least-once delivery, outbox |
| X14 | Common industry practice (no single source) | Engineering recommendations labelled `extension` |

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
`S5 A4 Insecure Direct Object Reference` · `S6 WSTG-ATHZ-04` · `S7 §1.2` · `X3`.

## 5. Coverage gaps

The corpus is strong on code-level craft (S1), architecture and dependency management (S2),
web application security review and testing (S5, S6), and the limits of analysis (S7). It is
thin or silent on:

- **Domain-Driven Design, design patterns catalogue, refactoring catalogue, legacy-code
  techniques** → extension rules citing X1–X4.
- **Testing strategy beyond unit tests** (pyramid, contract tests, property tests) → S1 Ch.9,
  S2 Ch.28 plus extensions.
- **Technical debt beyond Chapter 1** → S3 sample gives the definition, principal/interest, and
  the nine principles' statements; prioritisation mechanics in this skill are `synthesized`.
- **Reliability, performance, observability, API and database design, CI/CD** → mostly
  `extension`, with S1 Ch.13 (concurrency), S1 E1/E2 (one-step build/test), S5 logging and
  error-handling chapters, S6 configuration and API testing as anchors.
- **Language specifics** → S5 covers Java/.NET and some PHP for security; everything else is
  `convention` from official ecosystem guides (X11).
- **Non-web security** (embedded, mobile, cloud IAM, supply-chain attestation) → out of corpus
  scope; recommend specialist review.

## 6. Copyright and licensing

S1–S3 are copyrighted books. This skill contains only short paraphrases, structural
references (chapter and heuristic names), and original synthesis — no reproduced passages.
Keep it that way when extending the skill: paraphrase, cite the section, never paste text.
S5/S6 (Creative Commons) and S7 (CC BY-NC-ND) are likewise referenced, not redistributed.
Distribute the source PDFs separately and only as their licences allow.
