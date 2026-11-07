# Security rules, part 2: secure design, privilege, supply chain, gates and AI (SEC-*)

Design-time and pipeline security, from S8 Ch.3 and Ch.11 (attack trees, STRIDE, insecure design,
least privilege, the software supply chain, gate placement) plus external references for LLM
features. Code-level rules (injection, authorisation, sessions, crypto…) are in `security.md`.
Field meanings: `index.md`. Procedures: `../workflows/threat-modeling.md` (design) and
`../workflows/security-review.md` (code).

The governing reminders of `security.md` apply here too: pattern hits are leads, and "no findings"
never means "secure" (SEC-PROC-03, SEC-PROC-04).

Areas: DESIGN · PRIV · SUPPLY · GATE · AI

## DESIGN — threat modelling

### SEC-DESIGN-01 · Threat-model features that add assets, entry points or trust boundaries — before building them
- level: strong | severity: major | provenance: synthesized
- sources: S8 §3.7.1 (Attack Trees — the attacker's goal hierarchy; leaves become defences), §3.7.2 (Finding Possible Attacks — assets, trust boundaries, STRIDE per asset, social and procedural weaknesses; prune by feasibility, cheap high-damage attacks first; one tree per critical asset while writing stories), §11.2.3 (A06 Insecure Design — not findable by line-by-line review; addressed by threat modelling and design review), §11.1.4 (security as a quality attribute); S5 Methodology (threat modelling; STRIDE); S6 §2.5 (Threat Modeling)
- why: Design flaws — a reset flow that trusts a public answer, a webhook nobody authenticates, a tenant ID taken from the client — are invisible to code review and scanners because the code does exactly what was designed. They are cheapest to fix before the code exists.
- signals: New integrations, webhooks, file imports, admin features, multi-tenant data or payment flows designed without a list of threats; security discussed only at code review; mitigations that map to no named threat; security requirements missing from acceptance criteria.
- fix: For each feature that adds an asset, an entry point or a trust boundary, sketch actors, processes, data stores, flows and trust boundaries; walk STRIDE over every boundary-crossing flow and store (attack trees for the critical assets); rank threats by attacker cost and damage; turn the top mitigations into requirements, acceptance criteria and tests; record it with `../../assets/templates/threat-model.md` and revisit it when the design changes.
- verify: The design record lists ranked threats, each with a mitigation, an owner or an accepted risk; security acceptance criteria and tests exist for the top mitigations.
- related: SEC-PROC-01, SEC-BIZ-01, ARCH-QA-01, TEST-SEC-01

## PRIV — least privilege

### SEC-PRIV-01 · Every identity gets least privilege: services, tokens, automation and people
- level: strong | severity: major | provenance: synthesized
- sources: S8 §11.5 (Building Security In — secure defaults; least privilege for users, services and tokens; secrets management), §11.1.3 (defence in depth — layers that fail independently), §14.1.4 (shared responsibility — the customer secures configuration, code, data and access); X23 (least privilege; separation of privilege; complete mediation)
- why: Breaches spread through over-privileged identities: a leaked CI token with organisation-wide write access, a service account that reads every bucket, a database user that owns the schema. Least privilege turns the compromise of one part into a contained incident.
- signals: Service accounts or cloud roles with wildcard permissions; long-lived personal access tokens or API keys with full scope; CI jobs with write access to production and to every repository; shared administrator accounts; background workers running with the web tier's credentials; "temporary" grants never removed.
- fix: One identity per service and workload with only the permissions it uses (scoped tokens, per-service roles, short-lived credentials from the platform's workload identity); separate deployment, runtime and administrative identities; time-bound elevation for people; periodic review and removal of unused permissions.
- verify: Each service identity's permissions are listed and match its use (cloud access analyser or IAM report); CI tokens are scoped and short-lived.
- related: DATA-SEC-01, SEC-SECRET-01, SEC-SUPPLY-02, SEC-AUTHZ-03

## SUPPLY — software supply chain

### SEC-SUPPLY-01 · Vet dependencies before adopting them, inventory them, and keep watching them
- level: strong | severity: major | provenance: direct
- sources: S8 §11.4.1 (The Scale Problem — most code is third-party and transitive; version ranges can pull in malicious releases; lockfiles, exact pins, reviewed update PRs, threat-modelling new dependencies), §11.4.2 (Weak Links — maintainers are the weakest link; a dependency is an ongoing responsibility), §11.4.4 (Continuous Verification — Day 0 vetting of known vulnerabilities, static analysis, maintainer community and recent activity, package hygiene; Day 1 controlled ingestion; Day 2 production monitoring), §11.4.5 (OpenSSF Scorecard; Dependency-Check and Dependency-Track; SBOMs in CycloneDX or SPDX), §14.6.2 (typosquatting and maintainer compromise; each dependency is an engineering decision with a threat model)
- why: You inherit the security of every package you install, including the ones it installs. Abandoned packages stop receiving fixes, compromised maintainers ship backdoors (xz-utils), and a ubiquitous transitive dependency can hold a critical flaw nobody knew was present (Log4Shell). You cannot patch what you do not know you have.
- signals: New dependencies added without checking maintenance, maintainers or advisories; names resembling popular packages; install-time scripts that fetch remote code; no SBOM or dependency inventory; no advisory monitoring for deployed artifacts; vendored copies nobody updates.
- fix: Before adoption, check advisories, recent activity and maintainer base, package hygiene (signed releases, branch protection — Scorecard-style signals), licence, and whether an existing or smaller dependency would do; pin and lock; generate an SBOM per release; monitor advisories against the SBOMs of deployed artifacts (Dependency-Track or the platform's equivalent); review dependency-update PRs like code.
- verify: The change description lists each new dependency with the checks done; each release has an SBOM; advisory monitoring covers what is deployed.
- related: SEC-DEP-01, DLV-DEPS-01, DLV-DEPS-02, SEC-SUPPLY-02

### SEC-SUPPLY-02 · Protect build and release integrity: the reviewed source is what ships
- level: contextual | severity: major | provenance: direct
- sources: S8 §11.4.5 (SLSA build levels — provenance, signed provenance from a hosted builder, hardened build platform; Sigstore signing; SBOMs), §14.2.2 (the tested artifact is the deployed artifact; do not rebuild it), §14.6.2 (SolarWinds — malicious code inserted into a build process; artifact signing and provenance), §11.4.3 (xz-utils — backdoored release tarballs that differed from the git repository)
- applies: Services and libraries released through CI/CD, and anything distributed to customers or other teams.
- why: Whoever controls the build controls the product: an injected build step, a tampered release archive or a mutable third-party CI action ships malicious code that no source review sees.
- signals: Release artifacts built on developer machines; artifacts rebuilt per environment instead of promoted; third-party CI actions or base images referenced by mutable tags; long-lived secrets readable by jobs that run untrusted pull-request code; unsigned artifacts without provenance; release archives that differ from the tagged source.
- fix: Build once in hosted CI from a reviewed commit and promote that artifact; pin actions and base images by digest or commit SHA; short-lived, least-privilege pipeline credentials (OIDC) and no secrets in jobs triggered by untrusted code; sign artifacts and publish provenance (SLSA, Sigstore); verify signature and provenance before deploying; protect release branches and tags.
- verify: Deployed artifact digests match CI build outputs; provenance and signatures verify; CI configuration pins third-party components immutably.
- related: SEC-SUPPLY-01, DLV-DEPS-02, DLV-CI-01, SEC-PRIV-01

## GATE — security gates

### SEC-GATE-01 · Place security gates where they can answer, and tune them for precision
- level: strong | severity: minor–major | provenance: direct
- sources: S8 §14.6.3 (Secrets and Gate Placement — each gate at the earliest point it can answer correctly: secrets scanning and SAST at commit time, SCA at build time and on a schedule, DAST in staging), §14.6.1 (SAST, DAST and SCA), §11.3.1 (all three trade false positives against false negatives; noisy tools lose developer trust), §9.4.2 (precision buys trust; Google's target of roughly one false positive in ten)
- why: A gate that runs too late finds problems when they are expensive; one that runs too early cannot see what it needs (DAST needs a running application); an untuned gate fails builds on noise until people bypass it.
- signals: Secrets discovered only after reaching the remote repository; dependency audits run rarely or by hand; DAST never run, or run against production; thousands of untriaged SAST findings; security jobs allowed to fail silently; no scheduled re-scan of released dependencies.
- fix: Blocking secret scanning in pre-commit and on push; SAST on changed code in pull requests; SCA on every build plus scheduled scans of released artifacts; DAST against staging; baselines so only new findings block; triage with owners; measure and tune false-positive rates.
- verify: The pipeline shows each gate at its stage with its blocking policy; findings have owners and ages; a planted test secret is blocked before it reaches the remote.
- related: DLV-CI-01, DLV-SA-01, SEC-SECRET-01, SEC-DEP-01

## AI — LLM and agent features

### SEC-AI-01 · Treat LLM inputs and outputs as untrusted, and give agents least privilege
- level: contextual | severity: major–blocker | provenance: extension
- sources: X22 (prompt injection; sensitive information disclosure; improper output handling; excessive agency; system prompt leakage; unbounded consumption); X23 (least privilege; complete mediation); S8 §13.2.6 (assistant users wrote less secure code while feeling more confident), §13.8 (manage the new risks: security, provenance, hallucination, over-trust)
- applies: Features that call language models or agents: chat assistants, retrieval-augmented generation, summaries of user or third-party content, agents with tools, code generated at runtime.
- why: A model cannot reliably separate instructions from data, so any text it reads — a web page, an email, a document, a tool result — can redirect it; its output can carry markup, SQL or commands; and an agent's tools turn a successful injection into actions.
- signals: Model output rendered as HTML, executed, or interpolated into queries or shell commands without validation; retrieved documents or emails concatenated into prompts with system-level authority; agents holding broad credentials, or tools that move money, send email or delete data without confirmation; secrets or other users' data in prompts or system prompts; no limits on tokens, cost or tool calls.
- fix: Treat model output like user input — validate it against an expected schema and encode it for its sink (SEC-OUT-01, SEC-INJ-01); keep untrusted content marked as data that can never grant permissions; give tools least privilege, authorise every tool call server-side on behalf of the end user, and require human confirmation for consequential or irreversible actions; keep secrets out of prompts; enforce rate, token and cost limits; log tool calls for audit.
- verify: Tests with instructions injected into retrieved content cannot trigger privileged tool calls; model output reaches sinks only through validation and encoding; tools run with scoped credentials.
- related: SEC-OUT-01, SEC-INJ-01, SEC-PRIV-01, SEC-AUTHZ-01
