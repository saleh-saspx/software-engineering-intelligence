# PHP and Laravel

Conventions: PHP-FIG PSR-12 / PER Coding Style, PSR-4 autoloading, Laravel documentation (X11).
Laravel is a framework-centric platform: work with it (ARCH-DET-02, T-06). Do not import Java
or "enterprise" conventions into a Laravel codebase unless the project already uses them.

## Identify
- `composer.json`: `laravel/framework` version, PHP constraint, dev tools (Pest/PHPUnit, Larastan,
  Pint). `artisan` at the root; `app/`, `routes/`, `database/migrations`, `resources/views`.
- Laravel 11+ moved middleware and exception configuration into `bootstrap/app.php`; older versions
  use `app/Http/Kernel.php` and `app/Exceptions/Handler.php`. Check which before advising.

## Idioms to follow (and not flag)
- **Eloquent Active Record models** are the intended data layer; model scopes, accessors, casts and
  relationships on models are idiomatic (S1 Ch.6 treats Active Record as a data structure).
- **Facades and helpers** (`Cache::`, `Mail::`, `request()`, `auth()`) in controllers, jobs and
  commands are conventional and testable via fakes (`Mail::fake()`, `Queue::fake()`, `Http::fake()`).
  Keep them out of deep domain logic only where a rich domain core exists.
- **Route model binding**, **Form Requests** for validation, **API Resources** for response
  shaping, **Policies/Gates** for authorisation, **Jobs** for async work, **Events/Listeners**.
- **Don't propose** repository interfaces over Eloquent, DTO mapping layers, or hexagonal
  packaging for CRUD-heavy apps without a named force (DES-SIMP-03, ARCH-FIT-01). Extract
  Action/Service classes when controller methods contain growing business rules.
- Naming: singular `PascalCase` models (`Order`), plural snake_case tables (`orders`), controllers
  `OrderController`, methods `camelCase`. Formatter: Laravel Pint (PSR-12-based) if configured.

## Real issues to look for
- **Mass assignment**: `protected $guarded = [];` combined with `Model::create($request->all())`
  or `->update($request->all())` (S5 A4 over-posting; SEC-AUTHZ-03). Use `$fillable` plus
  `$request->validated()`.
- **Missing authorisation / IDOR**: `Order::find($id)` / `findOrFail($request->id)` without a
  policy check or ownership scope (`$request->user()->orders()->findOrFail($id)`,
  `$this->authorize('view', $order)`, `Gate::authorize`) (SEC-AUTHZ-02). Routes outside the
  `auth` middleware group (SEC-AUTHZ-01).
- **Raw SQL with interpolation**: `DB::raw("… $x")`, `whereRaw("… {$x}")`, `orderByRaw($request->sort)`,
  `DB::select("… '$x'")`. The `*Raw` methods accept bindings as a second argument — use them, and
  allow-list sort columns (SEC-INJ-01).
- **Unescaped Blade** `{!! $user->bio !!}` on user-controlled content (SEC-OUT-01).
- **N+1**: relations accessed in loops or Blade without `with()`; enable
  `Model::preventLazyLoading(! app()->isProduction())` to surface them (PERF-IO-01). Large exports
  without `chunk()`/`lazy()`/cursor (PERF-IO-02).
- **Business rules in controllers/Blade** that are growing and untested (DES-SRP-02); queries in
  Blade views (DATA-ACCESS-01).
- **Missing transactions** around multi-step writes (`DB::transaction(fn () => …)`) (REL-CONS-01).
- **`env()` outside config files**: once config is cached (`php artisan config:cache`), `env()`
  calls outside `config/*.php` return null — read via `config()` (DLV-CFG-01).
- **`APP_DEBUG=true` in production**, committed `.env`, keys in config files (SEC-CONF-01,
  SEC-SECRET-01).
- **CSRF exclusions** without reason (`$except` in `VerifyCsrfToken` or `validateCsrfTokens(except: …)`)
  (SEC-CSRF-01). **Open redirects** via `redirect($request->input('next'))` (SEC-REDIR-01).
- **Uploads** stored on the public disk with client file names, no MIME/size validation (SEC-FILE-01).
- **Non-idempotent queued jobs** that may be retried (REL-CONS-02); missing `$tries`/backoff thinking.
- Floats for money; use integer minor units or a money library (DATA-TYPE-01).

## Testing
PHPUnit or Pest; Feature tests with `RefreshDatabase`, model factories, `actingAs($user)`;
negative authorisation tests asserting 403/404 for another user's resource (TEST-SEC-01);
`Http::fake()` for outbound calls; database tests against the same engine as production when
queries are dialect-specific (TEST-DATA-01); Infection for mutation testing of critical code
(TEST-MUT-01).
Migrations: on PostgreSQL Laravel wraps migrations in a transaction — a concurrent index needs
`public $withinTransaction = false;` and `DB::statement('CREATE INDEX CONCURRENTLY …')`; keep
backfills out of schema migrations (queued, chunked jobs instead), avoid Eloquent models inside
migrations, and keep `down()` honest (DATA-MIG-01..03).

## Tools
`composer test` / `php artisan test`; Pint (format); Larastan/PHPStan (levels) or Psalm (incl.
taint analysis); Rector (upgrades); `composer audit` (advisories); deptrac (layer rules, if
layering is adopted); Laravel Debugbar/Telescope for query counts in development.
