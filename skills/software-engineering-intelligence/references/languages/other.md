# Other ecosystems (brief)

Short guidance for ecosystems without a dedicated file. Read the project's style configs and
the ecosystem's official guide; apply the generic rules only through those idioms (P-53).

## C# / .NET
- Conventions: `PascalCase` public members and types, `I`-prefixed interfaces (`IOrderService`) and
  `_camelCase` private fields are standard — not "encodings" to flag (T-11). Async methods end in
  `Async`. Enable nullable reference types for new code.
- Pitfalls: `async void` outside event handlers; blocking on tasks (`.Result`, `.Wait()`) causing
  deadlocks; missing `using`/`await using` for `IDisposable`/`IAsyncDisposable` (REL-RES-01);
  `HttpClient` created per request instead of `IHttpClientFactory`.
- EF Core: N+1 via lazy loading → `Include`; `AsNoTracking` for read-only queries; `FromSqlRaw` with
  concatenation is injectable, while interpolated APIs (`FromSqlInterpolated`, `FromSql` in EF Core 7+)
  parameterise (SEC-INJ-01).
- ASP.NET Core: `[Authorize]`/policies on controllers and minimal APIs; anti-forgery for cookie auth;
  `BinaryFormatter` is unsafe (SEC-INJ-03). Over-posting (S5 A4 covers MVC .NET binding) — bind to
  view models, not entities (SEC-AUTHZ-03).
- Tools: Roslyn analyzers, `dotnet format`, SonarAnalyzer, `dotnet list package --vulnerable`.

## Kotlin
- Null safety is the error model for absence; flag `!!` in production paths (CODE-ERR-04). Data
  classes for values; sealed classes + exhaustive `when` (CODE-CPLX-03).
- Coroutines: structured concurrency (no `GlobalScope` in application code), cancellation-aware
  suspending functions, `Dispatchers.IO` for blocking calls (REL-CONC-03).
- Tools: ktlint, detekt; Spring guidance from `java-spring.md` applies.

## Rust
- `Result` + `?` for errors; `unwrap`/`expect` acceptable in tests and truly-impossible cases with a
  message, not in request paths (CODE-ERR-02). Minimise and document `unsafe` (SEC-MEM-01).
- Tools: `cargo clippy`, `cargo fmt`, `cargo audit`/`cargo deny`, Miri for unsafe code.

## Ruby / Rails
- Rails is framework-centric like Laravel: ActiveRecord, concerns and conventions are idiomatic
  (ARCH-DET-02). Strong parameters (`permit`, never `permit!`) prevent mass assignment
  (SEC-AUTHZ-03); `includes`/`preload` for N+1 (PERF-IO-01); `html_safe`/`raw` on user content
  (SEC-OUT-01); string interpolation in `where("… #{x}")` (SEC-INJ-01).
- Tools: RuboCop, Brakeman (security), `bundle audit`, bullet (N+1 detection).

## C / C++
- Memory safety first (SEC-MEM-01): bounded functions, RAII and smart pointers in C++, no raw
  `new`/`delete` in modern code, sanitizers (ASan, UBSan, TSan) and fuzzing in CI.
- Undefined behaviour (signed overflow, uninitialised reads, strict aliasing) is a defect class of
  its own. Tools: clang-tidy, cppcheck, compiler warnings as errors.
