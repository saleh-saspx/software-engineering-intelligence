# Security rules (SEC-*)

Secure design and code review rules mapped to the OWASP Code Review Guide v2 (S5, sections
by its 2013 Top 10 numbering) and the Web Security Testing Guide v4.2 (S6, by test ID).
Field meanings: `index.md`. Procedure: `../workflows/security-review.md`.

Two reminders that govern every rule here:
- A pattern match is a **lead**, not a vulnerability. Confirm by tracing the data from an entry
  point to the sink and checking every control on the way (SEC-PROC-03, S7 §1.2).
- "No findings" never means "secure". State what was examined (SEC-PROC-04).

Areas: PROC · VAL · INJ · OUT · AUTHN · AUTHZ · SESS · CSRF · REDIR · SSRF · FILE · SECRET ·
CRYPTO · DATA · ERR · CONF · DEP · BIZ · RACE · CLIENT · API · MON · MEM

## PROC — process

### SEC-PROC-01 · Map entry points and trust boundaries before judging code
- level: strong | severity: — | provenance: direct
- sources: S5 Methodology (Determining the Attack Surface; threat modelling); S6 §2.5 (Threat Modeling); S6 §4.1.6 (WSTG-INFO-06 Identify Application Entry Points), §4.1.10 (WSTG-INFO-10 Map Application Architecture)
- why: Vulnerabilities live where untrusted data crosses into trusted code; without the map, review becomes random grepping.
- signals: Review notes with no list of routes, handlers, consumers, CLI inputs, file/queue readers, or third-party callbacks.
- fix: Inventory entry points (HTTP routes, GraphQL resolvers, message consumers, scheduled jobs reading external data, file uploads, webhooks), the identities that can reach them, and the data stores and external calls behind them.
- verify: Every finding can be placed on the map (entry point → sink).
- related: SEC-PROC-02, SEC-PROC-03

### SEC-PROC-02 · Rate findings by likelihood and impact, with assumptions stated
- level: strong | severity: — | provenance: direct
- sources: S5 Methodology (threat categorisation with STRIDE; DREAD and qualitative risk factors — S5 notes DREAD's subjectivity); S6 §2.11 (Security Test Data Analysis and Reporting)
- why: Severity without likelihood and exposure produces alarm fatigue; stating assumptions lets owners correct them.
- signals: Every finding marked "critical"; no mention of authentication requirements, exposure (internet vs. internal), or data sensitivity.
- fix: For each finding: who can reach it (anonymous/user/admin/internal), what they gain (confidentiality/integrity/availability impact, data class), preconditions. Map to blocker/major/minor (`../knowledge-model.md` §4.3).
- related: SEC-PROC-01

### SEC-PROC-03 · Pattern hits are leads; confirm by data flow
- level: strong | severity: — | provenance: synthesized
- sources: S5 Methodology (static code analysis tools; false positives; scanner limitations); S5 Appendix (Code Crawling); S7 Preface and §1.2 (approximation; soundness)
- why: Text patterns (`scripts/security_scan.py`, grep, SAST) over-report (sanitised inputs, test code) and under-report (indirect flows, framework magic).
- signals: Reports listing scanner hits as vulnerabilities without source-to-sink reasoning.
- fix: For each hit: identify the source of the data, every transformation and control, and the sink; mark `confirmed` only when the path is complete and the controls are absent or bypassable.
- related: AGT-EVID-02, SEC-PROC-04

### SEC-PROC-04 · Never certify security; state coverage and recommend specialist testing when warranted
- level: mandatory | severity: — | provenance: synthesized
- sources: S6 §2.2 (There is No Silver Bullet), §2.8 (The Need for a Balanced Approach); S7 §1.2
- why: Code review alone misses configuration, deployment and runtime issues; overclaiming creates false assurance.
- signals: Phrases like "the code is secure", "no vulnerabilities".
- fix: Say "no issues found in the reviewed scope (list), by these methods (list)"; list what was not covered; recommend penetration testing, dependency scanning, threat modelling or a specialist review for high-risk systems (payments, auth providers, crypto, multi-tenant isolation, safety-critical).
- related: AGT-EVID-03, AGT-SCOPE-01

## VAL — input validation

### SEC-VAL-01 · Validate untrusted input server-side at trust boundaries, by allow-list
- level: mandatory | severity: major–blocker | provenance: direct
- sources: S5 A1 Injection (input validation); S6 §4.7 (Input Validation Testing); S6 §4.10.1 (WSTG-BUSL-01 Business Logic Data Validation)
- why: Client-side checks are bypassed trivially; invalid data that reaches business logic causes logic abuse, crashes and injection.
- signals: Request data used without type/range/length/format checks; validation only in front-end code; deny-list filters (`str_replace("<script>", "")`); trusting hidden fields, headers, or IDs from the client.
- fix: Validate at the boundary with the framework's mechanism (Bean Validation, Laravel Form Requests, Pydantic, Zod, Go struct validation): types, ranges, lengths, formats, enumerations; reject rather than "fix" bad input.
- verify: Tests send out-of-range, oversized, wrong-type and malformed inputs and get controlled rejections.
- except: Validation is defence in depth — never the primary control against injection (use SEC-INJ-01) or XSS (use SEC-OUT-01).
- related: SEC-INJ-01, SEC-BIZ-01, TEST-SEC-01

## INJ — injection

### SEC-INJ-01 · Parameterise every query
- level: mandatory | severity: blocker | provenance: direct
- sources: S5 A1 Injection (SQL injection; parameterised queries); S6 §4.7.5 (WSTG-INPV-05 SQL Injection)
- why: String-built queries let data become code; this remains among the most damaging and most common web flaws.
- signals: Concatenation/interpolation into SQL (`"... WHERE id=" + id`, f-strings, `sprintf`, template literals); ORM escape hatches with interpolation (`DB::raw("…$x")`, `whereRaw("… $x")`, `.raw(f"…")`, `createQuery("… " + x)`, `Sequelize.literal`); dynamic `ORDER BY`/column names from input; NoSQL queries built from request JSON (`$where`, operator injection).
- fix: Bind parameters (`?`, `:name`, `$1`); allow-list identifiers (sort columns, directions) against fixed maps; use the ORM's query builder for dynamic filters.
- verify: Trace shows no user-controlled string reaches query text; a test with `' OR 1=1 --` / operator payloads behaves normally.
- auto: `scripts/security_scan.py` (lead), Semgrep/CodeQL/SpotBugs-FindSecBugs/Bandit/gosec.
- except: Identifiers that are compile-time constants.
- related: SEC-VAL-01, DATA-ACCESS-01
- example: ✗ `$db->select("SELECT * FROM orders WHERE status = '$status'")` → ✓ `$db->select('SELECT * FROM orders WHERE status = ?', [$status])`

### SEC-INJ-02 · Never build shell commands from input
- level: mandatory | severity: blocker | provenance: direct
- sources: S6 §4.7.12 (WSTG-INPV-12 Command Injection); S5 A1 Injection
- why: Shell metacharacters turn arguments into new commands.
- signals: `os.system`, `subprocess(..., shell=True)`, `Runtime.exec(String)`, `exec`/`shell_exec`/`system`/backticks in PHP, `child_process.exec`, `exec.Command("sh", "-c", …)` with interpolated input.
- fix: Use the library API instead of a command where possible; otherwise pass an argument vector without a shell, validate arguments by allow-list, and use `--` to end options.
- verify: Payloads like `; id` or `$(id)` are treated as literal arguments.
- related: SEC-VAL-01

### SEC-INJ-03 · No evaluation of untrusted code, templates or serialised objects
- level: mandatory | severity: blocker | provenance: synthesized
- sources: S6 §4.7.11 (WSTG-INPV-11 Code Injection), §4.7.18 (WSTG-INPV-18 Server-side Template Injection); unsafe deserialisation — X14 (not covered in S5/S6)
- why: `eval`, user-controlled templates and native deserialisation of untrusted bytes can give attackers code execution.
- signals: `eval`/`exec`/`Function()`/`assert($str)`; rendering user-supplied template strings (Jinja2 `Template(user_input)`, Twig/Blade from strings); `pickle.loads`, `yaml.load` without a safe loader, Java `ObjectInputStream.readObject`, PHP `unserialize` on request/cookie data, .NET `BinaryFormatter`.
- fix: Remove dynamic evaluation; render fixed templates with data; use data-only formats (JSON) with schema validation; safe loaders (`yaml.safe_load`); if native deserialisation is unavoidable, sign and allow-list types.
- verify: No eval/dynamic template/native deserialisation reachable from untrusted input (trace); safe loaders used.
- related: SEC-INJ-04, SEC-DEP-01

### SEC-INJ-04 · Treat every interpreter as an injection sink
- level: mandatory | severity: major–blocker | provenance: direct
- sources: S6 §4.7.6 (WSTG-INPV-06 LDAP), §4.7.7 (WSTG-INPV-07 XML Injection), §4.7.9 (WSTG-INPV-09 XPath), §4.7.10 (WSTG-INPV-10 IMAP/SMTP), §4.7.15 (WSTG-INPV-15 HTTP Splitting/Smuggling), §4.7.17 (WSTG-INPV-17 Host Header Injection); S5 A1 Injection
- why: LDAP filters, XPath, XML parsers (external entities), mail headers, HTTP headers and log formats all interpret data.
- signals: String-built LDAP/XPath queries; XML parsers with DTDs/external entities enabled; CRLF from input in headers or mail; absolute URLs built from the `Host` header (password-reset links).
- fix: Use parameterised/escaped APIs for each interpreter; disable DTD/external entities; strip CR/LF; build absolute URLs from configuration, not the request.
- verify: Parsers have external entities disabled (config/test); headers and interpreter queries are built via safe APIs.
- related: SEC-INJ-01, SEC-OUT-01

## OUT — output encoding

### SEC-OUT-01 · Encode output for its context; keep auto-escaping on
- level: mandatory | severity: major–blocker | provenance: direct
- sources: S5 A3 Cross-Site Scripting; S5 HTML5; S6 §4.7.1–4.7.2 (WSTG-INPV-01/02 Reflected/Stored XSS), §4.11.1 (WSTG-CLNT-01 DOM XSS), §4.11.3 (WSTG-CLNT-03 HTML Injection)
- why: Untrusted data rendered as HTML/JS executes in other users' sessions.
- signals: Raw-output constructs with untrusted data: Blade `{!! !!}`, Twig `|raw`, Jinja `|safe`/`Markup()`, Django `mark_safe`, React `dangerouslySetInnerHTML`, Vue `v-html`, Angular `bypassSecurityTrust*`, `innerHTML`/`outerHTML`/`document.write`/`insertAdjacentHTML`, `eval` of strings, `href` set from user data (`javascript:` URLs).
- fix: Use the framework's escaping by default; for rich text, sanitise with a maintained HTML sanitiser (e.g. DOMPurify) with an allow-list; validate URL schemes; add a Content Security Policy as defence in depth.
- verify: A stored `<img src=x onerror=alert(1)>` payload renders inert.
- related: SEC-VAL-01, SEC-CONF-01, SEC-CLIENT-01

## AUTHN — authentication

### SEC-AUTHN-01 · Protect credentials in transit and at rest with vetted mechanisms
- level: mandatory | severity: blocker | provenance: direct
- sources: S5 A2 Broken Authentication and Session Management; S6 §4.4.1 (WSTG-ATHN-01 Credentials over an Encrypted Channel), §4.9.4 (WSTG-CRYP-04 Weak Encryption)
- why: Plain or fast-hashed passwords are cracked offline after any database leak; credentials over HTTP are sniffed.
- signals: MD5/SHA-1/SHA-256 (unsalted or fast) password hashes; reversible encryption of passwords; home-made auth schemes; login forms or tokens over HTTP; passwords logged or emailed.
- fix: Use the framework's password hasher (bcrypt/scrypt/Argon2/PBKDF2 with appropriate cost); TLS everywhere; rely on maintained auth libraries/providers.
- verify: Password storage uses the framework hasher with adequate cost; all auth endpoints are HTTPS-only.
- related: SEC-CRYPTO-01, SEC-SECRET-01, SEC-DATA-02

### SEC-AUTHN-02 · Resist guessing, enumeration and reset abuse
- level: strong | severity: major | provenance: direct
- sources: S6 §4.4.3 (WSTG-ATHN-03 Weak Lock Out Mechanism), §4.3.4 (WSTG-IDNT-04 Account Enumeration), §4.4.7 (WSTG-ATHN-07 Weak Password Policy), §4.4.9 (WSTG-ATHN-09 Password Change or Reset)
- why: Unthrottled login, distinguishable error messages and weak reset tokens make account takeover cheap.
- signals: No rate limiting on login/OTP/reset endpoints; "user not found" vs. "wrong password" responses; predictable or long-lived reset tokens; reset links built from the Host header.
- fix: Rate-limit and/or lock with care (avoid lockout-as-DoS); uniform responses and timing; single-use, short-lived, random reset tokens; notify users of changes; offer MFA.
- verify: Tests show rate limiting after N attempts and identical responses for unknown users and wrong passwords.
- related: SEC-AUTHN-03, SEC-INJ-04

### SEC-AUTHN-03 · No default, shared or hard-coded credentials
- level: mandatory | severity: major–blocker | provenance: direct
- sources: S6 §4.4.2 (WSTG-ATHN-02 Default Credentials); S5 A5 Security Misconfiguration
- why: Default and embedded credentials are the first thing attackers try and cannot be rotated.
- signals: `admin/admin` seeds in production config; API keys or DB passwords in code; shared service accounts across environments.
- fix: Generate per-environment credentials at deploy time; store in a secret manager; force change of initial credentials.
- verify: Secret scanner and config review find no embedded or default credentials.
- related: SEC-SECRET-01

## AUTHZ — authorisation

### SEC-AUTHZ-01 · Enforce authorisation server-side on every protected function
- level: mandatory | severity: blocker | provenance: direct
- sources: S5 A7 Missing Function Level Access Control; S6 §4.5.2 (WSTG-ATHZ-02 Bypassing Authorization Schema), §4.5.3 (WSTG-ATHZ-03 Privilege Escalation)
- why: Hiding a button is not access control; any endpoint reachable by URL will be called.
- signals: Admin/privileged routes without role/permission middleware; checks done only in the UI; new endpoints added outside the group that applies auth middleware; GraphQL resolvers without checks.
- fix: Deny by default (auth middleware on route groups, method security, policies); check permissions in the server handler or a central policy layer; test unauthorised access.
- verify: Tests call each protected endpoint as anonymous, as a normal user and as another tenant and get 401/403/404.
- related: SEC-AUTHZ-02, SEC-API-01, TEST-SEC-01

### SEC-AUTHZ-02 · Check object-level access for every object reference (IDOR)
- level: mandatory | severity: blocker | provenance: direct
- sources: S5 A4 Insecure Direct Object Reference; S6 §4.5.4 (WSTG-ATHZ-04 Insecure Direct Object References)
- why: Authenticated users changing an ID in a URL or body to read or modify someone else's data is one of the most common real-world breaches.
- signals: `Model::find($request->id)`, `repo.findById(id)`, `get_object_or_404(Model, pk=pk)` with no ownership/tenant filter or policy check; tenant ID taken from the request instead of the session; bulk endpoints accepting ID lists.
- fix: Scope queries by the authenticated principal/tenant (`$user->orders()->findOrFail($id)`), or call a policy (`authorize('view', $order)`); use unguessable IDs only as defence in depth, never as the control.
- verify: A test where user B requests user A's object gets 403/404.
- related: SEC-AUTHZ-01, SEC-AUTHZ-03

### SEC-AUTHZ-03 · Least privilege and allow-listed binding (mass assignment)
- level: mandatory | severity: major–blocker | provenance: direct
- sources: S5 A4 (Binding issues in MVC — over-posting/mass assignment); S6 §4.5.3 (WSTG-ATHZ-03 Privilege Escalation), §4.10.2 (WSTG-BUSL-02 Ability to Forge Requests)
- why: Binding request bodies straight onto models lets attackers set fields such as `is_admin`, `role`, `price`, `owner_id`.
- signals: Laravel `$guarded = []` or `Model::create($request->all())`; Rails `permit!`; Spring binding entities directly from `@RequestBody`; Django `ModelForm` with `fields = '__all__'` on sensitive models; JS `Object.assign(user, req.body)`.
- fix: Allow-list fields (`$fillable`, `$request->validated()`, explicit DTOs/serializers, `strong parameters`); never bind security-relevant fields from client input.
- verify: A request adding `"role":"admin"` does not change the role.
- related: ARCH-DEP-03, SEC-VAL-01

## SESS — sessions

### SEC-SESS-01 · Sessions and tokens are protected throughout their lifecycle
- level: mandatory | severity: major | provenance: direct
- sources: S5 A2; S6 §4.6.1–4.6.3 (WSTG-SESS-01 Session Management Schema, -02 Cookie Attributes, -03 Session Fixation), §4.6.6–4.6.7 (WSTG-SESS-06 Logout, -07 Session Timeout), §4.6.9 (WSTG-SESS-09 Session Hijacking)
- why: Stolen or fixed session identifiers equal stolen accounts.
- signals: Cookies without `Secure`, `HttpOnly`, `SameSite`; no session ID rotation on login/privilege change; logout that doesn't invalidate server-side; no idle/absolute timeout; JWTs without expiry, with `alg: none`/unverified signatures, or long-lived without revocation.
- fix: Framework session defaults with secure flags; rotate on authentication; server-side invalidation; short-lived access tokens with refresh rotation; verify JWT signature and claims with a maintained library.
- verify: Response cookies carry Secure/HttpOnly/SameSite; session ID changes after login; logout invalidates server-side.
- related: SEC-CSRF-01, SEC-CLIENT-01

## CSRF

### SEC-CSRF-01 · Protect state-changing requests against CSRF when ambient credentials are used
- level: mandatory | severity: major | provenance: direct
- sources: S5 A8 Cross-Site Request Forgery; S6 §4.6.5 (WSTG-SESS-05 Cross Site Request Forgery)
- why: With cookie-based auth, a malicious site can trigger actions in the victim's session.
- signals: CSRF middleware disabled or routes excluded without reason; state changes via GET; `csrf_exempt`; SPA with cookie auth and no CSRF token/SameSite strategy.
- fix: Framework CSRF tokens on unsafe methods; `SameSite=Lax/Strict` cookies; no state change on GET.
- verify: A cross-origin form POST without a token is rejected (test).
- except: Pure bearer-token APIs (no ambient cookies) — still require CORS to be correct (SEC-CONF-01).
- related: SEC-SESS-01, API-IDEMP-01

## REDIR, SSRF, FILE

### SEC-REDIR-01 · No unvalidated redirects or forwards
- level: strong | severity: major | provenance: direct
- sources: S5 A10 Unvalidated Redirects and Forwards; S6 §4.11.4 (WSTG-CLNT-04 Client-side URL Redirect)
- why: Open redirects power phishing and OAuth token theft.
- signals: `redirect($request->next)`, `res.redirect(req.query.url)`, `return_to` parameters used unchecked.
- fix: Redirect only to relative paths or an allow-list of hosts; map tokens to destinations server-side.
- verify: A redirect parameter pointing to an external host is rejected or ignored (test).
- related: SEC-VAL-01

### SEC-SSRF-01 · Allow-list destinations for server-side requests built from input
- level: mandatory | severity: major–blocker | provenance: direct
- sources: S6 §4.7.19 (WSTG-INPV-19 Server-Side Request Forgery)
- why: Fetching user-supplied URLs lets attackers reach internal services and cloud metadata endpoints.
- signals: Webhook/URL-preview/import features calling `requests.get(url)`, `file_get_contents($url)`, `http.Get(userURL)`, `fetch(url)` with user-provided URLs.
- fix: Allow-list schemes and hosts; resolve and block private/link-local/metadata ranges (and re-check after redirects); use an egress proxy.
- verify: Requests to 127.0.0.1, 169.254.169.254 and private ranges are blocked, including via redirects (test).
- related: SEC-VAL-01, REL-TIME-01

### SEC-FILE-01 · Handle file paths and uploads defensively
- level: mandatory | severity: major–blocker | provenance: direct
- sources: S6 §4.5.1 (WSTG-ATHZ-01 Directory Traversal File Include), §4.10.8 (WSTG-BUSL-08 Upload of Unexpected File Types), §4.10.9 (WSTG-BUSL-09 Upload of Malicious Files)
- why: User-influenced paths read or overwrite arbitrary files; uploaded files can be executed or served as active content.
- signals: `open(base + filename)`, `include $_GET['page']`, `Path.of(dir, name)` without normalisation and containment check; uploads stored under the web root with original names; MIME type trusted from the client; no size limits; archive extraction without path checks ("zip slip").
- fix: Map identifiers to paths server-side; canonicalise and verify containment; store uploads outside the web root with generated names; validate type by content, enforce size limits; serve with `Content-Disposition: attachment` and correct `Content-Type`; scan if risk warrants.
- verify: Traversal payloads (../, encoded variants) are rejected; uploaded files cannot be executed or served inline.
- related: SEC-VAL-01, SEC-CONF-01

## SECRET, CRYPTO, DATA

### SEC-SECRET-01 · No secrets in source code, committed config, logs or client bundles
- level: mandatory | severity: blocker | provenance: direct
- sources: S5 A6 Sensitive Data Exposure; S5 A5 Security Misconfiguration; S6 §4.2.4 (WSTG-CONF-04 Old Backup and Unreferenced Files)
- why: Anything committed is copied to every clone, fork, CI log and backup; rotation is the only remedy once leaked.
- signals: API keys, passwords, private keys, tokens, connection strings with credentials in code, `application.properties`, `.env` committed, Docker images, front-end bundles; high-entropy strings; `.env.example` containing real values.
- fix: Remove and **rotate** the secret (history rewrite alone is not enough); load from environment/secret manager; add secret scanning (gitleaks/trufflehog) to pre-commit and CI.
- verify: Secret scanner clean on the change; the leaked credential has been rotated (ask — you cannot verify rotation).
- auto: `scripts/security_scan.py` (high-signal patterns), gitleaks, trufflehog, GitHub secret scanning.
- except: Clearly fake test fixtures (`test-key-not-real`) — still prefer generated values.
- related: SEC-AUTHN-03, DLV-CFG-01, SEC-DATA-02

### SEC-CRYPTO-01 · Use vetted cryptography correctly
- level: mandatory | severity: major–blocker | provenance: direct
- sources: S6 §4.9 (WSTG-CRYP-01 Weak TLS, -02 Padding Oracle, -03 Sensitive Information via Unencrypted Channels, -04 Weak Encryption); S5 A6 Sensitive Data Exposure
- why: Home-made or misused crypto fails silently: predictable tokens, decryptable data, disabled certificate checks.
- signals: `Math.random`/`rand()`/`random.random` for tokens; ECB mode; static IVs/nonces; hard-coded keys; DES/RC4/MD5/SHA-1 for security purposes; TLS verification disabled (`verify=False`, `InsecureSkipVerify: true`, `rejectUnauthorized: false`, trust-all `TrustManager`, `CURLOPT_SSL_VERIFYPEER => false`).
- fix: CSPRNG (`secrets`, `crypto.randomBytes`, `SecureRandom`, `random_bytes`, `crypto/rand`); authenticated encryption (AES-GCM, ChaCha20-Poly1305) via high-level libraries; keys from a KMS; keep TLS verification on (pin custom CAs instead of disabling).
- verify: Token generation uses a CSPRNG; TLS verification is enabled in all clients (inspection + config).
- related: SEC-AUTHN-01, SEC-DATA-01

### SEC-DATA-01 · Classify and protect sensitive data; minimise what you keep
- level: strong | severity: major | provenance: direct
- sources: S5 A6 Sensitive Data Exposure; S6 §4.9.3 (WSTG-CRYP-03); S6 §4.1.5 (WSTG-INFO-05 Webpage Content for Information Leakage)
- why: Data you don't store can't leak; over-broad API responses leak data the UI never shows.
- signals: Full card numbers, national IDs or health data stored without need; API responses including password hashes, tokens, internal flags; sensitive data in URLs (logged by proxies); caching of sensitive pages.
- fix: Minimise collection and retention; encrypt sensitive fields at rest where required; allow-list response fields; `Cache-Control: no-store` for sensitive responses.
- verify: Responses contain only allow-listed fields; sensitive fields are encrypted/absent where required.
- related: ARCH-DEP-03, DATA-PRIV-01, SEC-DATA-02

### SEC-DATA-02 · Logs contain no secrets or unnecessary personal data, and resist injection
- level: strong | severity: major | provenance: direct
- sources: S5 Reviewing Logging Code
- why: Logs are widely accessible and long-lived; tokens or passwords in logs are credentials; unescaped input can forge log entries.
- signals: Logging request bodies/headers wholesale (Authorization, cookies, passwords); exception messages containing connection strings; user input written to logs with newlines unescaped.
- fix: Structured logging with redaction of sensitive fields; never log credentials or full tokens; encode/strip control characters.
- verify: Log samples for auth flows show redacted secrets; CR/LF in input does not create new log lines.
- related: REL-OBS-01, CODE-ERR-03

## ERR, CONF, DEP

### SEC-ERR-01 · Fail closed and reveal nothing internal
- level: mandatory | severity: major | provenance: direct
- sources: S5 Error Handling; S6 §4.8.1 (WSTG-ERRH-01 Improper Error Handling), §4.8.2 (WSTG-ERRH-02 Stack Traces)
- why: Errors that default to "allow" bypass controls; stack traces and SQL errors give attackers a map.
- signals: `catch` blocks in auth/authz code returning success; debug pages enabled in production; raw exception messages returned in API responses.
- fix: Deny on error in security decisions; generic client messages with a correlation ID; full detail only in server logs.
- verify: Forcing an error returns a generic message and correlation ID; security checks deny on exception (test).
- related: CODE-ERR-01, API-ERR-01, SEC-CONF-01

### SEC-CONF-01 · Secure configuration by default
- level: strong | severity: major | provenance: direct
- sources: S5 A5 Security Misconfiguration; S6 §4.2.2 (WSTG-CONF-02 Application Platform Configuration), §4.2.5 (WSTG-CONF-05 Admin Interfaces), §4.2.6 (WSTG-CONF-06 HTTP Methods), §4.2.7 (WSTG-CONF-07 HSTS), §4.11.7 (WSTG-CLNT-07 CORS), §4.11.9 (WSTG-CLNT-09 Clickjacking)
- why: Frameworks ship developer-friendly defaults; production needs the opposite.
- signals: `DEBUG=True`/`APP_DEBUG=true` in production config; `Access-Control-Allow-Origin: *` with credentials, or reflecting any origin; missing HSTS/CSP/`X-Frame-Options` or `frame-ancestors`; exposed actuator/admin/debug endpoints; directory listing; permissive cloud storage ACLs.
- fix: Environment-specific config with secure production defaults; CORS allow-list; security headers via middleware; protect or disable admin/management endpoints.
- verify: Production config has debug off, restrictive CORS and security headers (inspect config/response headers).
- related: SEC-ERR-01, DLV-CFG-01

### SEC-DEP-01 · No components with known vulnerabilities — verified by a current scanner
- level: strong | severity: major–blocker | provenance: direct
- sources: S5 A9 Using Components With Known Vulnerabilities
- why: Most application code is third-party; one vulnerable transitive dependency can expose everything.
- signals: Outdated major versions of frameworks; no lockfile; no dependency scanning in CI; vendored copies of libraries.
- fix: Run the ecosystem's audit tool (`npm audit`, `pip-audit`, `composer audit`, `govulncheck`, OWASP Dependency-Check, `mvn dependency-check`, Dependabot/Renovate) and upgrade. Report advisories only from tool output or a current advisory database — not from memory.
- verify: The ecosystem audit tool reports no unresolved high/critical advisories (attach output).
- related: DLV-DEPS-01, DLV-DEPS-03, AGT-UNC-02

## BIZ, RACE

### SEC-BIZ-01 · Enforce business rules and workflows server-side
- level: strong | severity: major | provenance: direct
- sources: S6 §4.10 (WSTG-BUSL-01 Data Validation, -02 Forge Requests, -03 Integrity Checks, -04 Process Timing, -05 Function Use Limits, -06 Circumvention of Work Flows, -07 Defenses Against Application Misuse)
- why: Scanners can't find logic flaws: negative quantities, skipped checkout steps, coupons applied twice, prices taken from the client.
- signals: Prices/totals/discounts accepted from the client; multi-step flows where later steps don't verify earlier ones; no limits on usage-limited features; negative or zero quantities accepted.
- fix: Recompute security- and money-relevant values server-side; model workflows as explicit states with transition checks; enforce limits atomically.
- verify: Tests for out-of-order steps, replay, negative/huge values.
- related: SEC-RACE-01, SEC-VAL-01, REL-CONS-03

### SEC-RACE-01 · No race conditions in security- or money-relevant operations
- level: strong | severity: major–blocker | provenance: direct
- sources: S5 Race Conditions; S6 §4.10.4 (WSTG-BUSL-04 Process Timing)
- why: Check-then-act sequences (balance check then debit, coupon check then mark used) can be exploited with parallel requests.
- signals: Read-modify-write without transactions/locks; "if not exists then insert" without unique constraints; file existence checks before open (TOCTOU).
- fix: Atomic DB operations (`UPDATE … WHERE balance >= ?`), unique constraints, row locks/optimistic versioning, idempotency keys.
- verify: A concurrent test (parallel requests) cannot double-spend.
- related: REL-CONS-03, REL-CONC-01

## CLIENT, API

### SEC-CLIENT-01 · The client is untrusted territory
- level: contextual | severity: major | provenance: direct
- sources: S5 Client Side JavaScript; S5 Same Origin Policy; S6 §4.11.12 (WSTG-CLNT-12 Browser Storage), §4.11.11 (WSTG-CLNT-11 Web Messaging)
- why: Anything in the browser or mobile app can be read and modified by the user or by injected script.
- signals: Secrets/API keys in front-end bundles; authorisation decisions only in front-end code; long-lived tokens in `localStorage` in an app with XSS exposure; `postMessage` handlers without origin checks.
- fix: Keep secrets and authorisation server-side; prefer `HttpOnly` cookies or short-lived tokens; verify `event.origin`.
- except: Token storage choice is a trade-off (CSRF vs. XSS exposure) — report as a risk with context, not as an automatic vulnerability.
- related: SEC-OUT-01, SEC-SESS-01

### SEC-API-01 · Every API operation authenticates, authorises and limits
- level: strong | severity: major | provenance: direct
- sources: S6 §4.12.1 (WSTG-APIT-01 Testing GraphQL); S5 A7
- why: APIs expose more operations than UIs and are scripted easily; GraphQL adds introspection and query-cost abuse.
- signals: Unauthenticated internal endpoints reachable from outside; GraphQL resolvers without per-field/object authorisation; introspection enabled in production; no depth/complexity limits; no rate limits on expensive endpoints.
- fix: Auth middleware on all routes; per-resolver authorisation; query depth/cost limits; rate limiting; disable introspection where policy requires.
- verify: Every route/resolver is covered by auth middleware or an explicit public allow-list; limits configured.
- related: SEC-AUTHZ-01, API-PAGE-01

## MON, MEM

### SEC-MON-01 · Log and alert on security-relevant events
- level: contextual | severity: minor–major | provenance: direct
- sources: S5 Reviewing Security Alerts; S5 Review For Active Defence; S5 Reviewing Logging Code
- why: Undetected attacks continue; authentication failures, access-control denials and input-validation failures are the signals.
- signals: No logging of login failures, authorisation denials, admin actions; no alerting on spikes.
- fix: Emit structured security events (without secrets) and route them to monitoring.
- related: REL-OBS-01, SEC-DATA-02

### SEC-MEM-01 · Memory safety in unmanaged code
- level: mandatory | severity: blocker | provenance: direct
- sources: S5 Buffer Overruns
- why: Out-of-bounds writes give attackers code execution.
- signals: `strcpy`, `sprintf`, `gets`, unchecked `memcpy` lengths; manual index arithmetic on buffers; Rust `unsafe` blocks without justification.
- fix: Bounded functions, safe containers, sanitizers and fuzzing in CI; minimise and document `unsafe`.
- verify: Sanitizer/fuzzing runs are clean for the changed code paths.
- related: TEST-SEC-01
