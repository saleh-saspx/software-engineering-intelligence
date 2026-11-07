# Workflow: threat modelling and secure design review

Design-time security for a feature, system or change, before or alongside implementation. It
complements the code-level `security-review.md`: insecure design cannot be found by line-by-line
review or scanners, because the code does what was designed (S8 §11.2.3). Rules:
`../rules/security-design.md` and `../rules/security.md`. Template:
`../../assets/templates/threat-model.md`.

## Contents
1. When to do it · 2. Scope, assets and actors · 3. Model the system · 4. Find threats · 5. Rank ·
6. Mitigate with design principles · 7. Supply chain and pipeline · 8. LLM and agent features ·
9. Requirements and tests · 10. Record and revisit

## 1. When to do it
A feature that adds an **asset** (money, personal data, secrets), an **entry point** (endpoint,
webhook, file or URL import, message consumer, admin function), or a **trust boundary** (third
party, tenant, plug-in, language model), or that changes authentication, authorisation or crypto
(SEC-DESIGN-01). Keep it proportionate: a one-page table for most features; a workshop with
specialists for payments, identity, large-scale multi-tenant isolation (`security-review.md` §10).

## 2. Scope, assets and actors
What does an attacker want here? Who can reach each entry point — anonymous users, customers,
other tenants, administrators, partners, internal services, CI? What is out of scope, and what are
we assuming (TLS at the edge, a trusted identity provider)?

## 3. Model the system
Sketch external entities, processes, data stores and data flows; draw the trust boundaries; label
the data classes on each flow (credentials, personal data, payment data). Five to fifteen elements
is typical. Every flow that crosses a boundary gets examined in step 4.

## 4. Find threats
Walk STRIDE over each boundary-crossing flow and each store (S8 §3.7.2):

| | Ask | Typical controls |
|---|---|---|
| **S**poofing | Can someone pretend to be a user, a service or a provider? | Strong authentication and MFA; signed webhooks with timestamps; token audience and issuer checks; mutual TLS between services |
| **T**ampering | Can data be changed in transit, at rest, or by the client? | TLS; signatures or HMACs; server-side recomputation of prices and totals (SEC-BIZ-01); integrity constraints |
| **R**epudiation | Can an actor deny having done something? | Append-only audit trail written with the change (DATA-AUDIT-01); synchronised clocks |
| **I**nformation disclosure | Can data leak through responses, logs, errors, caches or another tenant? | Allow-listed response fields; log redaction; tenant scoping (DATA-TENANT-01); encryption |
| **D**enial of service | Can size, rate, cost or locks exhaust it? | Size and rate limits, quotas (PERF-SCALE-03), timeouts, queues, pagination |
| **E**levation of privilege | Can someone gain rights — IDOR, mass assignment, SSRF to internal services, plug-in escape? | Server-side authorisation on every object (SEC-AUTHZ-01, SEC-AUTHZ-02); allow-lists; least privilege (SEC-PRIV-01); isolation (ARCH-EXT-03) |

For each critical asset, an **attack tree**: the attacker's goal at the root, refined into routes
and concrete attacks — including social and procedural ones such as password resets by phone or
over-broad admin rights (S8 §3.7.1). Check these insecure-design patterns explicitly:
- identity, tenant, price or role taken from the client;
- webhooks without signature verification or replay protection;
- recovery flows that rely on public facts;
- the server fetching URLs supplied by users (SEC-SSRF-01);
- secrets shipped to clients; administrative actions without step-up authentication;
- language-model output used as commands, queries or markup (SEC-AI-01).

## 5. Rank
Defend cheap attacks with high damage first (S8 §3.7.2). Rate likelihood × impact with the
assumptions stated (SEC-PROC-02); a model where everything is "critical" helps nobody.

## 6. Mitigate with design principles
Choose mitigations with the classic design principles (X23; S8 §11.1.3, §11.5): least privilege;
fail-safe defaults (deny by default); complete mediation (check every access, every time); economy
of mechanism (a simple, vetted mechanism over a clever one); open design (no security through
obscurity); separation of privilege; defence in depth with layers that fail independently; and
secure defaults — make the default path the secure one. Map each mitigation to a rule and an owner.

## 7. Supply chain and pipeline
New dependencies (SEC-SUPPLY-01), build and release integrity (SEC-SUPPLY-02), pipeline identities
and secrets (SEC-PRIV-01), and where security gates run (SEC-GATE-01).

## 8. LLM and agent features
Trace which untrusted text reaches the model (user input, retrieved documents, emails, tool
results), where its output goes (HTML, SQL, shell, tools), which tools it can call with which
privileges, which actions need human confirmation, which limits apply to tokens, cost and tool
calls, and whether any secret sits in a prompt (SEC-AI-01, X22).

## 9. Requirements and tests
Turn each top mitigation into an acceptance criterion (Given/When/Then) and a negative test
(TEST-SEC-01); add WSTG test IDs for dynamic checks; express security quality goals as scenarios
(ARCH-QA-01, S8 §11.1.4).

## 10. Record and revisit
Fill the template; write ADRs for security-relevant decisions (ARCH-DEC-01); list residual risks
with an owner and a revisit trigger. Revisit when the design changes, a new entry point appears, or
an incident happens. Never conclude "secure" (SEC-PROC-04) — conclude "these threats, these
mitigations, these residual risks".
