# Code rules (CODE-*)

Local code quality: naming, functions, comments, errors, duplication, complexity, structure,
third-party boundaries. Field meanings, levels and severities: `index.md` and
`../knowledge-model.md` §4. Apply only after the context gates (`../knowledge-model.md` §5) —
especially ecosystem idioms (`../languages/`).

Areas: NAME · FUNC · CMNT · ERR · DUP · CPLX · STRUCT · BND

## NAME — naming

### CODE-NAME-01 · Names reveal intent and domain meaning
- level: strong | severity: minor–major | provenance: direct
- sources: S1 Ch.2 (Use Intention-Revealing Names; Use Problem Domain Names; Use Solution Domain Names); S1 N1, N2
- why: A name is the cheapest documentation and the one most often read; vague names force readers to reverse-engineer purpose, and that is where misunderstandings and defects start.
- signals: `data`, `info`, `tmp`, `obj`, `handle`, `process`, `manager` without qualification; single letters outside tiny scopes; names that describe type rather than role (`list1`, `strValue`); a comment needed to explain what a variable holds.
- fix: Rename to the role in the domain (`overdueInvoices`, `retryBudget`); use the business vocabulary the team uses. Use the IDE/language-server rename so all references move together.
- verify: A reader can say what the thing is for from its name alone; no explanatory comment is needed.
- auto: Linters catch only length/pattern issues; meaning needs review.
- except: Conventional short names in tiny scopes (`i` in a 3-line loop, `err` in Go, `ctx`, `t` in Go tests, `x`/`y` in math).
- related: CODE-NAME-02, CODE-NAME-04, DES-DOM-01
- example: ✗ `def calc(d): return d * 0.2` → ✓ `def vat_amount(net_price): return net_price * VAT_RATE`

### CODE-NAME-02 · One word per concept, used consistently
- level: strong | severity: minor | provenance: direct
- sources: S1 Ch.2 (Pick One Word per Concept; Don't Pun); S1 G11
- why: Synonyms (`fetch`/`get`/`retrieve`) make readers wonder whether behaviour differs; puns (one word for two concepts) hide real differences.
- signals: Parallel classes named `UserManager`, `OrderController`, `PaymentHandler` for the same role; `get` sometimes hitting the network and sometimes not.
- fix: Adopt the vocabulary already dominant in the codebase; rename the outliers in a dedicated, behaviour-preserving change.
- verify: grep for the synonym set shows a single dominant term per concept.
- related: CODE-NAME-01, ARCH-FIT-03

### CODE-NAME-03 · Names don't mislead, and they describe side effects
- level: strong | severity: minor–major | provenance: direct
- sources: S1 Ch.2 (Avoid Disinformation; Make Meaningful Distinctions); S1 N4, N7
- why: A wrong name is worse than a vague one — readers trust it. A function named like a query that mutates state or performs I/O causes defects at call sites.
- signals: `accountList` that is a map; `isValid()` that also saves; `getX()` that creates X if missing; `ProductInfo` vs `ProductData` with no difference; noise words (`theOrder`, `orderObject`).
- fix: Rename to the actual behaviour (`getOrCreateSession`, `validateAndSave` → split), or change the behaviour to match the name.
- verify: Each call site's expectations match the behaviour.
- related: CODE-FUNC-03

### CODE-NAME-04 · Searchable names and named constants; name length grows with scope
- level: strong | severity: minor | provenance: direct
- sources: S1 Ch.2 (Use Searchable Names; Avoid Mental Mapping); S1 N5, G25
- why: Magic numbers and cryptic abbreviations can't be found or changed safely; a constant used in three places drifts.
- signals: Literal `86400`, `0.2`, `3` (retries), status strings repeated; abbreviations only the author understands.
- fix: Introduce named constants or enums close to their meaning; keep configurable values out of code (see CODE-STRUCT-04).
- verify: Changing the value requires editing one place.
- except: `0`, `1`, `-1`, `2` in obvious arithmetic; well-known formulas; test fixtures where the literal *is* the point.
- related: CODE-STRUCT-04, DLV-CFG-01

### CODE-NAME-05 · Ecosystem naming conventions win over generic advice
- level: strong | severity: nit–minor | provenance: convention
- sources: S1 G24 (Follow Standard Conventions), N3, N6; X11
- why: Readers fluent in the ecosystem parse idiomatic names instantly; "clean code" names that fight the idiom slow them down.
- signals: `snake_case` in Java, `IUserService` in Python, Hungarian prefixes in TypeScript; Go getters named `GetName()`; exported Go identifiers stuttering (`user.UserService`).
- fix: Follow the language guide in `../languages/` and the project's existing style; fix via formatter/linter rules when possible.
- verify: The project linter's naming rules pass; names match surrounding code.
- except: The project has a documented deviating convention — then that convention wins (P-53).
- related: CODE-STRUCT-02, AGT-CONV-01

## FUNC — functions

### CODE-FUNC-01 · A function does one thing, at one level of abstraction
- level: strong | severity: minor–major | provenance: direct
- sources: S1 Ch.3 (Small!; Do One Thing; One Level of Abstraction per Function; Reading Code from Top to Bottom); S1 G30, G34
- why: Mixed levels force readers to switch between policy and plumbing; each extra responsibility is another reason to change and another path to test. Length correlates with this but is not the criterion (T-01).
- signals: Section comments inside a body (`// validate`, `// save`); the honest name needs "and"; high-level calls interleaved with string parsing or byte handling; deep nesting.
- fix: Extract each phase into a well-named function; keep the top-level function as a readable sequence of steps (stepdown rule).
- verify: The function can be described in one sentence without "and"; extracted parts can be tested alone.
- auto: Length and complexity outliers via `scripts/hotspots.py` — pointers, not verdicts.
- except: Linear, single-level code that reads top-down (common in Go/C, migrations, scripts, `main`); hot loops where call overhead matters (measured); extractions that would need 4+ parameters signal the wrong seam.
- related: CODE-FUNC-02, CODE-CPLX-01, DES-SRP-01
- example: ✗ `placeOrder()` validates, prices, writes SQL, and sends email inline → ✓ `placeOrder()` calls `validate(order)`, `price(order)`, `orders.save(order)`, `notifier.orderPlaced(order)`.

### CODE-FUNC-02 · Few, meaningful parameters; no boolean flag arguments
- level: contextual | severity: minor | provenance: direct
- sources: S1 Ch.3 (Function Arguments; Flag Arguments; Argument Objects); S1 F1, F3, G15
- why: Long parameter lists are easy to call wrongly (especially same-typed neighbours); a flag argument means the function does two things.
- signals: More than ~4 parameters; adjacent parameters of the same type; `render(true)`, `save(user, false, true)`.
- fix: Split flag functions (`renderForPrint` / `renderForScreen`); group parameters that travel together into a value/options object; use named/keyword arguments where the language supports them.
- verify: Call sites read unambiguously without IDE hints.
- except: Keyword-only/named arguments (Python, Kotlin, C#) mitigate much of the risk; constructors for value objects; framework callbacks with fixed signatures.
- related: CODE-FUNC-01, DES-DOM-01

### CODE-FUNC-03 · No hidden side effects
- level: strong | severity: major | provenance: direct
- sources: S1 Ch.3 (Have No Side Effects); S1 N7
- why: Callers reason from the name; a hidden write, global mutation, or network call creates defects far from their cause and temporal couplings nobody knows about.
- signals: Query-named functions that write, cache globally, or call remote services; functions that mutate their input arguments unexpectedly; module-level mutable state changed in helpers.
- fix: Rename to reveal the effect, or split into a pure part and an effectful part; return new values instead of mutating inputs.
- verify: Tests show the function's observable effects match its name; no test needs to reset hidden global state.
- related: CODE-NAME-03, CODE-FUNC-04, CODE-FUNC-05

### CODE-FUNC-04 · Separate commands from queries; avoid output arguments
- level: contextual | severity: minor | provenance: direct
- sources: S1 Ch.3 (Command Query Separation; Output Arguments); S1 F2
- why: A function that both changes state and returns information invites misuse (`if (set("x", v))`); output arguments read backwards.
- signals: Boolean-returning setters used in conditions; functions filling a passed-in list or buffer in languages that can return values.
- fix: Split into a command and a query, or return a result object.
- except: Idiomatic APIs (`map.put` returning the old value, `Interlocked` operations, Go's `Read(p []byte)`, builder/fluent APIs); performance-sensitive buffer reuse.
- related: CODE-FUNC-03

### CODE-FUNC-05 · Make temporal coupling explicit
- level: strong | severity: minor–major | provenance: direct
- sources: S1 G31 (Hidden Temporal Couplings)
- why: When calls must happen in order but nothing enforces it, a future edit will reorder them.
- signals: `init()` must precede `run()` with no guard; methods that depend on fields set by an earlier call; comments like "must call X first".
- fix: Pass the output of one step as the input of the next ("bucket brigade"), use constructors/builders that produce only valid states, or encode the state machine in types.
- verify: Calling steps out of order is impossible or fails loudly.
- related: CODE-FUNC-03, REL-CONS-01

## CMNT — comments

### CODE-CMNT-01 · Comments explain why, constraints and warnings; public APIs are documented
- level: strong | severity: minor | provenance: synthesized
- sources: S1 Ch.4 (Good Comments: Explanation of Intent, Clarification, Warning of Consequences, TODO Comments, Amplification, Javadocs in Public APIs); S5 (security rationale in code review); T-05
- why: Code says what and how; only prose can say why a non-obvious choice was made, what must not be changed, or what a public contract promises.
- signals: Surprising code (workaround, odd ordering, deliberate inefficiency, security-relevant check) with no explanation; exported/public API without doc comments in a library; TODOs with no owner or ticket.
- fix: Add a brief *why* comment or link to the ADR/ticket; document public APIs in the ecosystem's doc format; give TODOs an issue reference.
- verify: A newcomer can tell why the surprising line exists and whether it is safe to change.
- related: CODE-CMNT-02, ARCH-DEC-01, DLV-DOC-02

### CODE-CMNT-02 · No redundant, obsolete or misleading comments
- level: strong | severity: minor–major | provenance: direct
- sources: S1 Ch.4 (Bad Comments: Redundant, Misleading, Mandated, Noise); S1 C1–C4
- why: Comments are not compiled or tested, so they rot; a stale comment actively misleads.
- signals: Comment restates the code (`i++ // increment i`); comment contradicts the code; mandated boilerplate docblocks with no content; closing-brace and position-marker comments.
- fix: Delete noise; correct or delete stale comments; prefer a better name or extracted function over a "what" comment.
- verify: Each remaining comment adds information the code cannot express.
- except: Mandated licence headers; generated code; documentation generators that require a stub.
- related: CODE-CMNT-01, CODE-NAME-01

### CODE-CMNT-03 · No commented-out code or journal comments
- level: strong | severity: nit–minor | provenance: direct
- sources: S1 C5 (Commented-Out Code); S1 Ch.4 (Journal Comments; Attributions and Bylines)
- why: Version control keeps history; commented-out code accumulates because nobody dares delete it.
- signals: Blocks of commented code; change logs and author names at the top of files.
- fix: Delete; reference the commit if the history matters.
- verify: No commented-out blocks remain in the diff; history is reachable via VCS.
- related: CODE-STRUCT-01

## ERR — error handling

### CODE-ERR-01 · Errors are never silently swallowed
- level: mandatory | severity: major–blocker | provenance: synthesized
- sources: S1 Ch.7 (Error Handling); S5 Error Handling; S6 §4.8 (WSTG-ERRH-01); S1 G4
- why: A swallowed error turns a visible, local failure into silent data corruption or a far-away, undiagnosable one. In security code it can turn "deny" into "allow".
- signals: Empty `catch {}` / `except: pass` / `rescue nil`; Go `_ = f()` or unchecked `err`; `.catch(() => {})`; ignored return codes from write/close/commit; logging and continuing where the operation's result is required.
- fix: Handle (recover meaningfully), propagate with context, or fail fast. If an error is truly ignorable, make that explicit with a comment saying why and, where it matters, a metric.
- verify: A test or reasoning shows the failure path surfaces to a caller, a log with context, or a user-facing error.
- auto: Linters such as `errcheck`/`staticcheck` (Go), Bandit/ruff rules (Python), ESLint `no-empty` (JS/TS), SpotBugs (Java); `scripts/security_scan.py` flags some patterns.
- except: Best-effort cleanup where failure is irrelevant (e.g. closing a read-only file after a successful read) — still say so in code.
- related: CODE-ERR-02, REL-ERR-01, SEC-ERR-01
- example: ✗ `try: charge(card) except Exception: pass` → ✓ `try: charge(card) except PaymentDeclined as e: return Declined(reason=e.code)` (let unexpected errors propagate).

### CODE-ERR-02 · Use the ecosystem's error model, consistently
- level: strong | severity: minor–major | provenance: synthesized
- sources: S1 Ch.7 (Use Exceptions Rather Than Return Codes; Use Unchecked Exceptions; Define the Normal Flow); X11; T-02
- why: Mixing exception styles, sentinel values and error returns in one codebase makes every call site uncertain. S1's exception advice is right for Java-like languages and wrong for Go or Rust.
- signals: Go code using `panic` for expected failures; Java/Python returning `-1`/`None` to signal errors among exception-based APIs; Rust `unwrap()` in non-test paths; catch-all handlers deep inside business logic.
- fix: Exceptions in exception languages (handled at boundaries); `error` values wrapped with `%w` in Go; `Result` + `?` in Rust; one translation layer at the edge (HTTP/CLI) that maps errors to responses.
- verify: Error-handling style is uniform within a module; the boundary handler is the single place that maps errors to outputs.
- related: CODE-ERR-01, CODE-ERR-03, API-ERR-01

### CODE-ERR-03 · Errors carry context and are typed by what callers need
- level: strong | severity: minor | provenance: direct
- sources: S1 Ch.7 (Provide Context with Exceptions; Define Exception Classes in Terms of a Caller's Needs)
- why: "error: failed" costs hours; callers need to distinguish only the cases they handle differently.
- signals: Bare re-throws losing the cause; messages without the operation or identifiers; dozens of exception types callers never distinguish, or one generic type where callers must parse messages.
- fix: Wrap with operation and key identifiers (not secrets); preserve the cause chain; define error types per distinct caller reaction.
- verify: A log line alone identifies what failed, for which entity, and why.
- related: CODE-ERR-02, SEC-DATA-02

### CODE-ERR-04 · Absence is explicit and checked
- level: strong | severity: minor–major | provenance: synthesized
- sources: S1 Ch.7 (Don't Return Null; Don't Pass Null); S1 G26 (Be Precise); T-12
- why: Unchecked null/None is the most common runtime crash; where the type system can express absence, let it.
- signals: Returning `null` for "not found" where callers don't check; nullable parameters used as mode switches; TypeScript without `strictNullChecks`; Kotlin `!!`; Python functions that return `None` on one path implicitly.
- fix: Return empty collections instead of null; use Optional/nullable types/`T | None` with checks enforced by the type checker; Special Case/Null Object where it simplifies callers; validate at boundaries.
- verify: Type checker (strict mode) passes; tests cover the "absent" path.
- related: CODE-ERR-01, DLV-SA-02

## DUP — duplication

### CODE-DUP-01 · Unify true duplication
- level: strong | severity: minor–major | provenance: synthesized
- sources: S1 G5 (Duplication); S1 Ch.12 (No Duplication); S2 Ch.16 (Duplication)
- why: Knowledge repeated in several places must be changed in all of them; one gets missed, producing inconsistent behaviour.
- signals: The same business rule (tax, eligibility, validation) implemented in several places; copy-pasted blocks that were edited together in past commits; parallel switch statements on the same type.
- fix: Extract the shared knowledge into one function, type, or module owned by the right component; replace repeated type switches with polymorphism or a table (CODE-CPLX-03).
- verify: The rule changes in one place; git history of the copies shows they co-changed (true duplication).
- auto: Copy-paste detectors (PMD CPD, jscpd); co-change analysis via git log.
- related: CODE-DUP-02, CODE-CPLX-03

### CODE-DUP-02 · Don't unify accidental duplication
- level: strong | severity: minor–major | provenance: direct
- sources: S2 Ch.16 (Duplication — true vs. accidental); S2 Ch.7 (SRP); T-04
- why: Code that looks the same but serves different actors will diverge; merging it couples those actors so a change for one breaks the other.
- signals: A proposed shared helper with growing flag parameters; "common" modules imported by unrelated features; DTOs shared across bounded contexts or services.
- fix: Keep separate copies when the reasons for change differ; if already merged and now forking via flags, split it back.
- verify: Each copy has a single owner/actor; no flags select between callers' behaviour.
- related: CODE-DUP-01, DES-SRP-01, ARCH-DOM-01

## CPLX — complexity and conditionals

### CODE-CPLX-01 · Keep control flow reviewable; use complexity as a pointer
- level: contextual | severity: minor–major | provenance: synthesized
- sources: S5 Methodology (cyclomatic complexity bands and bad-fix probability); S1 Ch.3 (Blocks and Indenting); S8 §10.3.1 (cyclomatic complexity as decisions plus one, with its own interpretation bands), §15.3 (code smells suggest problems but do not prove them); T-13; T-18
- why: Each decision adds paths to understand and test; S5 links rising complexity to higher regression ("bad fix") probability, and uses it to decide where review should start.
- signals: Cyclomatic complexity above ~10–15 per function; nesting deeper than ~3; long `if/else if` ladders; functions few people dare to touch.
- fix: Guard clauses/early returns; extract predicates and branches; replace conditional ladders with lookup tables or polymorphism; split by responsibility.
- verify: Complexity reduced without behaviour change (tests green before and after).
- auto: `scripts/hotspots.py` (approximate decision counting; exact for Python), or language tools (radon, gocyclo, PMD, ESLint `complexity`).
- except: Parsers, state machines and validation tables can be legitimately branchy if regular and table-like. Never use thresholds as hard gates without team agreement.
- related: CODE-FUNC-01, TD-PRI-01

### CODE-CPLX-02 · Encapsulate conditionals; avoid negatives and obscured intent
- level: optional | severity: nit–minor | provenance: direct
- sources: S1 G28 (Encapsulate Conditionals), G29 (Avoid Negative Conditionals), G19 (Use Explanatory Variables), G16 (Obscured Intent)
- why: `if (shouldRetry(response))` reads faster than a compound boolean; double negatives cause logic slips.
- signals: Compound conditions with 3+ terms inline; `if (!notReady)`; dense one-liners and clever tricks.
- fix: Extract a well-named predicate or explanatory variable; invert negatives.
- related: CODE-CPLX-01, CODE-NAME-01

### CODE-CPLX-03 · Replace repeated type switches with polymorphism or dispatch
- level: contextual | severity: minor | provenance: direct
- sources: S1 Ch.3 (Switch Statements); S1 G23 (Prefer Polymorphism… — the "ONE SWITCH" rule); T-08
- why: The same switch on a type tag scattered across modules means every new case edits all of them (an OCP violation).
- signals: The same `switch(type)` / `if kind == …` chain in two or more places.
- fix: One switch that builds polymorphic objects (factory), or a dispatch table/map; in languages with sealed types and exhaustive pattern matching, an exhaustive `match` is an acceptable alternative.
- verify: Adding a case touches one place (or the compiler lists every place).
- except: A single switch (S1's own allowance); exhaustively checked sum types (Rust, Kotlin sealed, TypeScript discriminated unions with `never` checks).
- related: DES-OCP-01, CODE-DUP-01

### CODE-CPLX-04 · Encapsulate boundary conditions
- level: strong | severity: minor–major | provenance: direct
- sources: S1 G33 (Encapsulate Boundary Conditions), G3 (Incorrect Behavior at the Boundaries); S1 T5
- why: Off-by-one, empty, max-size and inclusive/exclusive mistakes cluster at boundaries.
- signals: `+1`/`-1` scattered through an algorithm; `<=` vs `<` inconsistencies; untested empty and single-element cases; date-range edges.
- fix: Compute boundary values once into named variables; prefer half-open ranges consistently; add boundary tests (TEST-BND-01).
- verify: Boundary tests (empty, one, max, edge dates) pass; boundary values are computed in one named place.
- related: TEST-BND-01

## STRUCT — structure and hygiene

### CODE-STRUCT-01 · Remove dead code and clutter
- level: strong | severity: minor | provenance: direct
- sources: S1 G9 (Dead Code), F4 (Dead Function), G12 (Clutter)
- why: Dead code is read, maintained, and sometimes accidentally revived; it also hides real dependencies.
- signals: Unreferenced functions/classes, unreachable branches, unused parameters/imports, feature flags permanently on/off.
- fix: Delete (VCS keeps history). Check for reflection, dynamic dispatch, framework conventions and public API consumers first.
- verify: Build, tests and a reference search (including string-based lookups) pass after removal.
- auto: Compiler warnings, `vulture` (Python), `ts-prune`/`knip` (TS), `deadcode`/`staticcheck` (Go), IDE inspections.
- except: Public library APIs (deprecate first); code invoked by name (routes, DI, serializers).
- related: CODE-CMNT-03

### CODE-STRUCT-02 · The project's formatter and linter decide layout
- level: strong | severity: nit | provenance: convention
- sources: S1 Ch.5 (Team Rules), G24; X11
- why: Formatting debates waste review time; consistent layout lets diffs show real changes.
- signals: Mixed styles; manual formatting changes in diffs; no formatter configured.
- fix: Use the project's formatter (gofmt, Black/ruff format, Prettier, PHP-CS-Fixer/Pint, google-java-format/Spotless) and run it on changed files only, in a separate commit if broad.
- verify: Formatter check passes in CI.
- except: Never reformat files you are not otherwise changing (AGT-MIN-01).
- related: AGT-MIN-01, DLV-SA-01

### CODE-STRUCT-03 · Vertical locality and newspaper ordering
- level: optional | severity: nit | provenance: direct
- sources: S1 Ch.5 (Vertical Formatting: Newspaper Metaphor, Vertical Distance, Vertical Ordering); S1 G10
- why: Related code close together and callers above callees let a file read top-down.
- signals: Helpers far from their single caller; variables declared long before use.
- fix: Reorder within the file when already editing it.
- related: CODE-FUNC-01

### CODE-STRUCT-04 · Keep configurable data at high levels
- level: strong | severity: minor | provenance: direct
- sources: S1 G35 (Keep Configurable Data at High Levels); S1 G25
- why: Defaults and tunables buried deep in low-level code are hard to find and change per environment.
- signals: Timeouts, URLs, limits, feature switches hard-coded in leaf functions.
- fix: Lift to configuration or top-level constants and pass them down; environment-specific values go to config (DLV-CFG-01).
- verify: Changing the value per environment needs no code edit.
- related: CODE-NAME-04, DLV-CFG-01

### CODE-STRUCT-05 · Don't override safeties without a recorded reason
- level: strong | severity: minor–major | provenance: direct
- sources: S1 G4 (Overridden Safeties); S1 T4
- why: Disabled tests, suppressed warnings, `// @ts-ignore`, `# type: ignore`, `@SuppressWarnings`, `nolint` hide the very problems tools exist to catch.
- signals: Suppressions without a reason; skipped tests without ticket; disabled compiler checks; lowered linter levels in a PR.
- fix: Fix the underlying issue, or add a specific, reasoned, narrowly scoped suppression.
- verify: Each suppression names the rule and the reason.
- related: TEST-SKIP-01, DLV-SA-01

## BND — third-party boundaries

### CODE-BND-01 · Own the boundary to volatile third-party code
- level: contextual | severity: minor–major | provenance: synthesized
- sources: S1 Ch.8 (Using Third-Party Code; Exploring and Learning Boundaries; Clean Boundaries); S2 Ch.32 (Frameworks Are Details); P-07
- why: Vendor APIs change, leak types everywhere, and are hard to fake in tests; a thin adapter you own localises that churn.
- signals: SDK types (`S3Client`, `Stripe\Charge`, `requests.Response`) passed deep into business logic; the same vendor call pattern copy-pasted across modules; tests that need the real service.
- fix: Introduce an adapter/gateway exposing only what the application needs, in its own terms; write learning tests for unclear vendor behaviour.
- verify: Swapping or faking the vendor touches one module.
- except: Stable standard libraries; the framework deliberately chosen as the application's platform (ARCH-DET-02); one-off scripts.
- related: ARCH-DET-01, DES-DIP-01, TEST-BEH-02
