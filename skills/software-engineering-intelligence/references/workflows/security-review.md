# Workflow: security review

A risk-based secure code review following the OWASP Code Review Guide methodology (S5) and the
Web Security Testing Guide (S6). Rules: `../rules/security.md`. Output:
`../../assets/templates/review-report.md` with the security fields filled in.

## Contents
1. Frame the review · 2. Map the attack surface · 3. Model threats · 4. Collect leads ·
5. Review controls systematically · 6. Confirm by tracing · 7. Rate and report · 8. Security across
the lifecycle · 9. Where controls live in common frameworks · 10. When to call in specialists ·
11. OWASP Top 10:2025 map

For a design that is not yet built — or to check the design behind the code — use
`threat-modeling.md` first: design flaws cannot be found line by line (S8 §11.2.3).

## 1. Frame the review
- **Assets**: what must be protected (accounts, money, personal data, secrets, availability).
- **Actors**: anonymous users, authenticated users, other tenants, admins, internal services,
  third-party callbacks.
- **Exposure**: internet-facing or internal; authentication model; deployment environment.
- **Scope**: diff, module, or application; languages and frameworks; what is explicitly out of
  scope (infrastructure, mobile client, third-party services).

## 2. Map the attack surface (SEC-PROC-01)
List entry points with who can reach them:
- HTTP routes and their middleware groups; GraphQL schema and resolvers; WebSocket handlers.
- Message consumers, scheduled jobs that read external data, webhooks, file imports, CLI tools
  that accept external input.
- Outbound calls built from input (SSRF candidates), file system access, template rendering,
  query construction, deserialisation, command execution — the **sinks**.
Fast indexes: route files (`routes/*.php`, `urls.py`, `@RequestMapping`/`@GetMapping`,
`app.get/router.*`, `http.HandleFunc`/router registrations), and `scripts/security_scan.py`.
Also map the non-code attack surface the change touches: new dependencies, CI workflow changes,
service identities and their permissions, LLM prompts and tools (SEC-SUPPLY-01/02, SEC-PRIV-01,
SEC-AI-01).

## 3. Model threats
For each entry point (or group), ask STRIDE questions briefly (S5 Methodology; S6 §2.5): can an
actor **S**poof identity, **T**amper with data, **R**epudiate actions, cause **I**nformation
disclosure, **D**enial of service, or **E**levate privilege? Note trust boundaries crossed and the
data classes involved. Keep it proportionate: a table of 5–15 lines is usually enough.

## 4. Collect leads
- `python scripts/security_scan.py PATH` (add `--include-tests` only if tests could ship) — a
  pattern crawl in the spirit of S5's Code Crawling appendix. Every hit is `possible` until traced.
- The project's SAST (Semgrep, CodeQL, SpotBugs/FindSecBugs, Bandit, gosec, Psalm taint, ESLint
  security plugins) and dependency audit (`npm audit`, `pip-audit`, `composer audit`,
  `govulncheck`, OWASP Dependency-Check) if available — report advisories from tool output only.
- Secret scanning (gitleaks/trufflehog) if available; otherwise the scan's secret patterns.

## 5. Review controls systematically
Walk through each control family against the attack-surface map. For each, find **where the
control is implemented** and **whether every relevant entry point passes through it**.

| Family | Key rules | Key questions |
|---|---|---|
| Authentication | SEC-AUTHN-01..03 | Password storage, credential transport, throttling, reset flow, defaults |
| Sessions/tokens | SEC-SESS-01, SEC-CSRF-01 | Cookie flags, rotation, logout, expiry, JWT verification, CSRF |
| Authorisation | SEC-AUTHZ-01..03, SEC-API-01 | Function-level checks on every route; object-level ownership/tenant on every lookup; mass assignment |
| Input validation | SEC-VAL-01, SEC-BIZ-01 | Server-side, allow-list, at the boundary; business values recomputed server-side |
| Injection | SEC-INJ-01..04 | Every query/command/template/parser built from input; spreadsheet exports of user text |
| Output encoding | SEC-OUT-01, SEC-CLIENT-01 | Raw-HTML sinks; URL schemes; client-side DOM sinks |
| Files, URLs, redirects | SEC-FILE-01, SEC-SSRF-01, SEC-REDIR-01 | Paths, uploads, outbound requests, redirects |
| Crypto and secrets | SEC-CRYPTO-01, SEC-SECRET-01 | CSPRNG, algorithms, TLS verification, key and secret handling |
| Data protection | SEC-DATA-01/02, DATA-PRIV-01 | Response fields, logs, caching, retention |
| Errors and config | SEC-ERR-01, SEC-CONF-01 | Fail closed; no internals leaked; production defaults; CORS; headers |
| Concurrency and logic | SEC-RACE-01, SEC-BIZ-01 | Double-spend, workflow skipping, limits |
| Dependencies and supply chain | SEC-DEP-01, SEC-SUPPLY-01/02 | Known-vulnerable components (tool output); vetting of new packages; pinned CI actions; build provenance |
| Privilege | SEC-PRIV-01, DATA-SEC-01 | Service accounts, tokens and database roles scoped to their use |
| LLM features | SEC-AI-01 | Untrusted text reaching prompts; model output reaching sinks; tool privileges |
| Monitoring | SEC-MON-01 | Security events logged and alertable |
| Memory safety | SEC-MEM-01 | Unmanaged code only |

## 6. Confirm by tracing (SEC-PROC-03)
For each lead: **source** (which entry point, which actor) → **transformations and controls**
(validation, encoding, parameterisation, authorisation, framework protections) → **sink**.
- Complete path, no effective control → **confirmed vulnerability** (or `likely` if one unknown
  remains, e.g. a global middleware you couldn't see — state it).
- Control present but weak or bypassable → **potential vulnerability** (`likely`/`possible`).
- No exploit path now, but defence in depth is missing → **hardening recommendation**.
- Can't tell without information you lack → **unverified concern** (`question`).
Don't stop at the first finding in a file; the same pattern usually repeats.

## 7. Rate and report (SEC-PROC-02)
- Likelihood (reachability, required privileges, attack complexity) × impact (confidentiality,
  integrity, availability, data class, blast radius) → severity: exploitable by anonymous or any
  user with high impact → blocker; requires privileges or has limited impact → major; hardening
  → minor.
- Each finding: location, source→sink summary, impact, fix (in the framework's idiom), severity,
  confidence, rule ID, and the S6 test ID that verifies it (e.g. WSTG-ATHZ-04), so a tester can
  confirm it dynamically.
- **Coverage section is mandatory** (SEC-PROC-04): entry points and control families reviewed;
  what wasn't (infrastructure, client apps, third-party services); tools run and not run.
- Never conclude "secure". Conclude "no issues found in <scope> by <methods>" when that is true.

## 8. Security across the lifecycle
Security is part of every workflow in this skill, following the phases of S6 Ch.3:

| Phase | Activity in this skill |
|---|---|
| Requirements | Capture security requirements and abuse cases with the feature (implementation.md §2) |
| Design | Threat model new entry points and trust boundaries; decide control placement; ADR for security-relevant choices (architecture-review.md) |
| Implementation | Secure defaults; checklist §5 items 3–5 in self-review |
| Code review | Security pass in every review (code-review.md §4) |
| Database/API | Parameterisation, least-privilege DB users, response allow-lists, rate limits |
| Dependencies | Justify, pin, audit (DLV-DEPS-*, SEC-DEP-01) |
| Configuration | Production defaults, secrets management, headers, CORS (SEC-CONF-01, DLV-CFG-01) |
| Testing | Negative tests for each control (TEST-SEC-01); WSTG test IDs for dynamic testing |
| Deployment | Gate: no secrets, no critical advisories, debug off (code-review.md §9) |
| Maintenance | Patch cadence, monitoring of security events (SEC-MON-01) |

## 9. Where controls live in common frameworks
Use this to find (or notice the absence of) central controls before flagging per-endpoint issues.

| Framework | Authentication / authorisation | Input validation | Query safety | Output encoding |
|---|---|---|---|---|
| Laravel | `auth` middleware on route groups; Policies/Gates (`authorize`, `can`), `Gate::before` | Form Requests, `$request->validate()` | Eloquent/query builder bindings; danger: `DB::raw`, `*Raw()` | Blade `{{ }}` escapes; danger: `{!! !!}` |
| Spring | Spring Security filter chain, `@PreAuthorize`/method security | Bean Validation `@Valid` | JPA/JdbcTemplate parameters; danger: string-built JPQL/SQL | Thymeleaf escapes by default; danger: `th:utext` |
| Django | `login_required`, permissions, DRF permission classes | Forms/serializers | ORM; danger: `raw()`, `extra()`, cursor with f-strings | Templates escape; danger: `mark_safe`, `|safe` |
| Express/Nest | Middleware (passport, guards in Nest) | Zod/Joi/class-validator | Parameterised driver/ORM; danger: template-literal SQL | Template engine escaping; React escapes; danger: `dangerouslySetInnerHTML` |
| Go (net/http, gin, chi) | Middleware wrappers per route group | Struct binding + validator | `database/sql` placeholders; danger: `fmt.Sprintf` SQL | `html/template` escapes; danger: `text/template` for HTML, `template.HTML` |

## 10. When to call in specialists
Recommend dedicated security expertise or testing — penetration test, cryptographic review,
threat-modelling workshop, cloud/IAM review — when the system handles payments, authentication
for others (identity provider), healthcare or other regulated data, multi-tenant isolation at
scale, custom cryptography, safety-critical functions, or when the code review found systemic
control gaps. Code review complements but does not replace dynamic testing (S6 §2.8). AI-driven
scanners and penetration agents can help, but only against systems the user is authorised to test,
and their findings still need human validation (S8 §11.3.2).

## 11. OWASP Top 10:2025 map
S8 §11.2 uses the 2025 edition; S5 uses 2013 numbering. Treat categories as buckets of weaknesses,
not a checklist (S8 §11.2).

| 2025 category | Rules |
|---|---|
| A01 Broken Access Control (includes SSRF and CSRF) | SEC-AUTHZ-01..03, SEC-API-01, SEC-SSRF-01, SEC-CSRF-01, DATA-TENANT-01 |
| A02 Security Misconfiguration | SEC-CONF-01, DLV-CFG-01, SEC-ERR-01 |
| A03 Software Supply Chain Failures | SEC-SUPPLY-01, SEC-SUPPLY-02, SEC-DEP-01, DLV-DEPS-01..03 |
| A04 Cryptographic Failures | SEC-CRYPTO-01, SEC-AUTHN-01, SEC-DATA-01 |
| A05 Injection (includes XSS) | SEC-INJ-01..04, SEC-OUT-01, SEC-VAL-01 |
| A06 Insecure Design | SEC-DESIGN-01, SEC-BIZ-01, SEC-RACE-01, ARCH-EXT-03 |
| A07 Authentication Failures | SEC-AUTHN-01..03, SEC-SESS-01 |
| A08 Software or Data Integrity Failures | SEC-SUPPLY-02, SEC-INJ-03, DATA-EVOL-01 |
| A09 Security Logging and Alerting Failures | SEC-MON-01, SEC-DATA-02, DATA-AUDIT-01 |
| A10 Mishandling of Exceptional Conditions | SEC-ERR-01, CODE-ERR-01, REL-ERR-01 |
