# Patterns in languages and frameworks

What common framework features really are, which names mislead, and the idiomatic form of each
pattern per ecosystem. Before saying "this uses pattern X", map the participants and check the
defining property (DES-PAT-04); framework vocabulary is not evidence (T-27). Mechanism details
come from the frameworks' documentation (X11); classifications are the skill's judgment (X14).

## Contents
1. Java / Spring Boot · 2. PHP / Laravel · 3. Go · 4. Python · 5. TypeScript / React ·
6. Cross-cutting checks

## 1. Java / Spring Boot

| Feature | What it is | Watch for |
|---|---|---|
| Dependency injection, `@Configuration`, `@Bean` | Inversion of control with a composition root — not a GoF pattern (`index.md` §3) | Field injection hides dependencies; prefer constructors (DES-DI-01) |
| Singleton scope (the default) | One instance per container, injected — not the Singleton pattern | Mutable state in singleton beans is shared across requests and threads |
| Prototype scope | A new instance per lookup — not the Prototype pattern (no copying) | Injecting a prototype-scoped bean into a singleton yields one instance unless looked up per use |
| Proxy-based AOP: `@Transactional`, `@Cacheable`, `@PreAuthorize`, `@Async`, `@Retryable` | Proxy (JDK dynamic proxies or generated subclasses) | Calls from inside the same bean bypass the proxy; final or private methods are not intercepted; checks must not rely on it alone (SEC-DESIGN-02) |
| `List<PaymentGateway>` / `Map<String, PaymentGateway>` injection | A Strategy registry assembled by the container | Unknown keys must fail loudly (DES-PAT-05); `@Primary`/`@Qualifier` choices are hidden wiring |
| `FactoryBean<T>` | A creation hook for complex beans (Factory Method in spirit; `getObject()`) | Prefer a plain `@Bean` method unless the factory itself needs lifecycle |
| `ApplicationEventPublisher`, `@EventListener` | Observer inside the process; listeners run synchronously in the publisher's thread and transaction by default | A failing listener propagates to the publisher; slow listeners slow requests |
| `@TransactionalEventListener` | Observer bound to a transaction phase (after commit by default) | Not durable — lost on crash; use an outbox for integration events (T-30) |
| `JdbcTemplate`, `RestTemplate`, `TransactionTemplate` | A template with callbacks — the fixed skeleton calls functions you pass in (T-25) | Not inheritance-based Template Method; don't subclass them |
| `OncePerRequestFilter.doFilterInternal`, `AbstractRoutingDataSource` | Inheritance-based Template Method hooks | Override only the documented hook |
| Servlet `Filter` chain, Spring Security filter chain, `HandlerInterceptor` | Chain of Responsibility (pipeline variant): a filter may stop the request | Order and registration scope; new paths must be covered |
| `HttpServletRequestWrapper`, `BeanPostProcessor` wrapping beans | Decorator (wrapper with the same interface) / Proxy | Keep the wrapped contract |
| `HandlerAdapter`, Spring Integration channel adapters, your outbound ports | Adapter | Keep translation thin and errors mapped |
| Lombok `@Builder` | Generated Builder without validation | Add validation; prefer records with compact constructors when fields are all required |

Idioms: records and sealed interfaces with exhaustive `switch` replace many State and Visitor uses
(Java 21); enum singletons when one is truly needed (X15 Item 3); `Function<…>`/`Supplier<…>` for
one-method strategies and commands; X15 Item 1 static factories are not Factory Method (T-26).

## 2. PHP / Laravel

| Feature | What it is | Watch for |
|---|---|---|
| Service container, `bind`, `singleton`, `scoped` | Dependency injection container; `app()`/`resolve()` calls are Service Locator | Locator calls inside domain classes (DES-DI-02); `singleton` is container scope, not the pattern |
| Facades (`Cache::`, `Mail::`, real-time facades) | Static proxies to container services — Service Locator plus Proxy, not GoF Facade (T-27) | Conventional in controllers and jobs; avoid in domain code; fakes via `Facade::fake()` |
| `Illuminate\Pipeline`, HTTP middleware | Chain of Responsibility (pipeline): each pipe calls `$next` or stops | Middleware registered per route can miss new routes; ordering in the kernel/bootstrap |
| Events and listeners, model observers | Observer; queued listeners (`ShouldQueue`) run asynchronously | Dispatching inside a transaction — use after-commit dispatch for side effects |
| Managers and drivers (cache, queue, mail, filesystem, custom `Manager` classes) | Strategy selection by name plus factory methods (`createXDriver`) — an API over drivers, bridge-like | Unknown drivers must fail at boot; keep driver config per environment |
| Notifications and channels | Bridge-like: notification content (`via`, `toMail`, `toArray`) over delivery channels | Channels carry their own credentials and validation |
| Jobs, commands, `dispatch()` | Command objects, serialised onto queues | Validate and authorise at handle time; jobs must be idempotent (REL-CONS-02) |
| Eloquent models | Active Record — not a GoF pattern; collections are iterators with a fluent API | Lazy loading in loops (PERF-IO-01); mass assignment (SEC-AUTHZ-03) |
| Macros, `Macroable` | Run-time extension of framework classes | Hidden behaviour; register in a service provider and document |

Idioms: constructor injection in services; small invokable classes or closures for one-method
strategies; enums with methods (PHP 8.1+) for simple state machines.

## 3. Go

| Need | Idiomatic form | Avoid |
|---|---|---|
| Strategy, Command, Template steps | Function types (`type PriceRule func(Cart) Discount`) or one-method interfaces | Class hierarchies with an interface per behaviour and a factory per implementation |
| Builder | Functional options or a config struct | Java-style builders with setters |
| Singleton | A package-level value with `sync.Once`, or better, a value passed in | Global mutable variables reached from everywhere |
| Decorator, middleware | `func(http.Handler) http.Handler` wrappers; `io.Reader`/`io.Writer` wrappers (`bufio`, `gzip`) | Wrappers that may stop a request are chain handlers — name them so (T-27) |
| Adapter | A small struct satisfying your interface; interfaces are declared by the consumer | Interfaces declared next to their only implementation |
| Iterator | Range-over-func iterators (`iter.Seq`), slices, or channels with cancellation | Channels without a way to stop the producer (goroutine leaks) |
| Visitor | Type switches over a closed set | Double-dispatch boilerplate |
| Template Method | A function receiving the varying steps as functions or an interface | Struct embedding as inheritance: an embedded type's methods cannot call the outer type's overrides |

Interfaces are satisfied implicitly — an interface with one implementation is not a Strategy until
there is variation; a function value is not a Command unless something stores, queues or undoes it
(DES-PAT-04).

## 4. Python

| Need | Idiomatic form | Watch for |
|---|---|---|
| Strategy, Command | Callables (functions, `functools.partial`, objects with `__call__`) | Class-per-behaviour hierarchies (DES-PAT-06) |
| `@decorator` syntax | A function wrapping a function at definition time — Decorator- or Proxy-like for functions; some decorators only register (`@app.route`) | Not the GoF Decorator unless it wraps an object with the same interface (T-27) |
| Singleton | A module-level object or a cached function; modules are imported once | `__new__`-based singletons; mutable module state across tests |
| Builder | Keyword arguments with defaults, dataclasses, validation in `__post_init__` | Builders for simple records |
| Iterator | Generators and the iteration protocol | Hand-written iterator classes |
| Template Method | Django class-based views, `unittest.TestCase`, context managers for set-up and tear-down | Overriding undocumented hooks |
| Visitor | `ast.NodeVisitor`; `functools.singledispatch` or structural pattern matching (`match`) | Visitors over two types |
| Observer | Django signals, SQLAlchemy events, blinker | Signals are synchronous and run inside the transaction — use `transaction.on_commit` for side effects |
| Interfaces | `typing.Protocol` (structural) or `abc.ABC` | ABCs with one subclass |

## 5. TypeScript / React

| Feature or need | What it is | Watch for |
|---|---|---|
| Structural typing, objects of functions | Strategies and commands as plain functions or objects | Interfaces plus classes for one-function behaviours (DES-PAT-06) |
| Custom hooks | Encapsulated stateful behaviour — not a GoF pattern; often an Adapter over a browser or library API | Hooks hiding network calls behind innocent names |
| Higher-order components | Decorator-like wrappers of components | Deep wrapper stacks; prefer hooks |
| Render props, callback props | Strategy-like injection of behaviour | Prop drilling |
| Context providers | Scoped dependency injection — not Singleton | Re-render cost; hidden dependencies |
| Redux actions and reducers, state stores | Command-like actions handled by reducers; subscriptions are Observer | Logic scattered across actions, thunks and reducers |
| Express/Koa/Next middleware | Chain of Responsibility (pipeline) | Error middleware ordering; routes registered outside the protected group |
| RxJS | Observer plus Iterator over asynchronous streams | Unsubscribed subscriptions (leaks) |
| TypeScript decorators (`@Injectable`, `@Controller`) | Metaprogramming annotations for frameworks (Angular, NestJS DI) — not GoF Decorator | Naming them as the pattern (T-27) |
| Discriminated unions with exhaustive `switch` | Replaces State classes and Visitor in many cases | Missing `never` exhaustiveness checks |
| Module-level instances | One per module loader or bundle | In server-side rendering, module state is shared across requests and users — never keep per-user data there |

## 6. Cross-cutting checks
- **Name by mechanism first**, then by pattern if the participants match (DES-PAT-04).
- **Container scopes are not creational patterns**: singleton and prototype scopes describe lifetimes.
- **Wrappers protect only what passes through them**: proxies, middleware and decorators can be
  bypassed (SEC-DESIGN-02).
- **Framework events are not messaging**: in-process listeners are neither durable nor ordered across
  processes (T-30).
- **Follow the framework's extension points** (P-53) and keep your domain logic in plain classes and
  functions behind them.
