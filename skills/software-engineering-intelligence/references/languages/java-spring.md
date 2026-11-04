# Java and Spring

Conventions here are `convention` provenance (X11: Oracle/Google Java style, Spring docs) unless
a rule ID says otherwise. Check the project's own build plugins and configs first — they win.

## Identify
- `pom.xml` / `build.gradle(.kts)`: Java release (`maven.compiler.release`, toolchains), Spring Boot
  version (parent or plugin). Boot 3 uses `jakarta.*` packages; Boot 2 uses `javax.*`.
- Layout: `src/main/java`, `src/main/resources/application*.yml|properties`,
  `src/main/resources/db/migration` (Flyway) or Liquibase changelogs; tests in `src/test/java`.

## Idioms to follow (and not flag)
- Naming: `PascalCase` types, `camelCase` members, `UPPER_SNAKE` constants, lowercase packages. No
  wildcard imports when the formatter/style forbids them (T-03 — S1 J1 is superseded).
- Constructor injection with `final` fields (often via Lombok `@RequiredArgsConstructor` if the
  project uses Lombok — don't flag Lombok itself).
- Records for immutable DTOs (Java 16+). `Optional` as a return type for "maybe absent"; avoid it
  for fields and parameters.
- Unchecked exceptions for application errors, translated to HTTP responses in one place
  (`@ControllerAdvice` / `@ExceptionHandler`, `ProblemDetail` in Spring 6) — CODE-ERR-02.
- JPA entities need no-arg constructors and accessors; that's a framework requirement, not a
  DES-OBJ-01 violation.
- Layered `controller/service/repository` structure is normal; in larger apps prefer package by
  feature/component with package-private classes (S2 Ch.34, ARCH-BND-02/03).

## Real issues to look for
- **Field injection** (`@Autowired` on fields) in new code — hides dependencies (DES-DI-01).
- **Mutable state in singleton beans** — Spring beans are singletons by default, so mutable
  instance fields are shared across concurrent requests (REL-CONC-01).
- **`@Transactional` pitfalls** — self-invocation inside the same class bypasses the proxy (no
  transaction); transactions on private methods do nothing with proxy-based AOP; remote calls
  inside transactions (DATA-TXN-01); catching exceptions inside a transactional method so it
  commits partial work (REL-CONS-01).
- **Entities exposed in APIs** — returning JPA entities from controllers leaks fields and triggers
  lazy loading during serialisation (ARCH-DEP-03, SEC-DATA-01). Use DTOs/records.
- **N+1 queries** — lazy associations accessed in loops; `spring.jpa.open-in-view` (enabled by
  default, Boot logs a warning) hides them in the web layer. Use `JOIN FETCH`, `@EntityGraph`,
  batch fetching; consider disabling open-in-view (PERF-IO-01).
- **Swallowed exceptions** — `catch (Exception e) { log…; return null; }` (CODE-ERR-01, CODE-ERR-04).
- **Unbounded queries** — `findAll()` on large tables; use `Pageable` (PERF-IO-02, API-PAGE-01).

## Security hot spots (S5 focuses on Java — see its A1–A10 sections)
- String-built SQL/JPQL (`createQuery("… " + x)`, `JdbcTemplate` with concatenation) → bind
  parameters (SEC-INJ-01).
- Binding request bodies straight onto entities (over-posting, S5 A4) → DTOs with allow-listed
  fields (SEC-AUTHZ-03).
- Missing method/URL security: endpoints outside the secured filter chain; `@PreAuthorize`
  absent where object ownership matters (method security needs `@EnableMethodSecurity` in Spring
  Security 6) (SEC-AUTHZ-01/02).
- `csrf().disable()` (or the lambda DSL equivalent) copied from tutorials into session-based apps
  (SEC-CSRF-01) — fine only for stateless token APIs.
- Actuator exposure (`management.endpoints.web.exposure.include=*`) without protection (SEC-CONF-01).
- Polymorphic deserialisation with Jackson default typing; `ObjectInputStream` on untrusted data
  (SEC-INJ-03). XML parsers without XXE protection (`DocumentBuilderFactory` features) (SEC-INJ-04).
- Secrets in `application.properties` committed to the repo (SEC-SECRET-01).
- `Runtime.exec`/`ProcessBuilder` with concatenated input (SEC-INJ-02); SpEL evaluation of input.

## Testing
JUnit 5, AssertJ, Mockito; slice tests (`@WebMvcTest`, `@DataJpaTest`) for boundaries;
Testcontainers for real databases (TEST-DATA-01); ArchUnit to enforce layering (ARCH-BND-02);
`@SpringBootTest` sparingly (slow). Avoid mocking JPA repositories to test query logic.

## Tools
Build: Maven/Gradle wrapper (`./mvnw test`, `./gradlew test`). Format/lint: Spotless,
google-java-format, Checkstyle, PMD, Error Prone. Bugs/security: SpotBugs + FindSecBugs, Semgrep,
CodeQL. Dependencies: OWASP Dependency-Check, `mvn versions:display-dependency-updates`,
Dependabot/Renovate. Coverage: JaCoCo.
