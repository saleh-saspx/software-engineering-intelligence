# Chain of Responsibility · behavioural

**Intent** — Pass a request along a chain of handlers; each handler either processes it or forwards
it to the next (S10).

**Example (real problem)** — Expense claims are approved by the lowest authority allowed to approve
the amount: team lead up to 500, department head up to 5,000, finance director above that. Each
handler checks its limit and approves or forwards; finance later puts a fraud-screening handler at
the front without touching the others. HTTP middleware (authentication, rate limiting, logging) is
the same idea in a pipeline form.

- **Problem** — A sender hard-codes a sequence of checks or a choice of receiver; adding, removing or
  reordering steps means editing an ever-growing method.
- **Context** — Several potential handlers; the right one, or the set and order of steps, varies or
  is configured.
- **Motivation** — Decouple senders from receivers; make each step a standalone object; configure
  the chain.
- **Applicability** — Different kinds of requests processed in various ways when the exact kinds and
  their sequence are not known in advance; several handlers that must run in a particular order;
  handler sets or orders that change at run time (S10).
- **Structure** — Handler interface (`handle(request)`); an optional base handler holding the next
  link; concrete handlers; a client assembling the chain.
- **Participants and responsibilities** — Handler: handles, passes, or both. Client: builds the chain
  and sends requests to its head.
- **Collaborations** — The request travels until a handler deals with it or the chain ends.
- **Implementation considerations** — Two variants: first match (stop once handled) and pipeline
  (every handler acts and passes on, as middleware does); be ready for a chain of one link, a
  request stopped half-way and a request that falls off the end unhandled (S10); avoid cycles;
  assemble the chain in one place (DES-PAT-05).
- **Consequences** — Flexible ordering and composition; behaviour depends on configuration.
- **Benefits** — Control over processing order; senders decoupled from performers (SRP); new
  handlers without client changes (OCP) (S10).
- **Trade-offs** — Configurability versus traceability of who handled what.
- **Costs** — Some requests may end up unhandled (S10); following a request through a long chain
  while debugging.
- **Known misuses** — Fixed chains where a plain sequence of calls is clearer; fall-through meaning
  "allowed" in security checks; handlers depending on undocumented side effects of earlier ones;
  using a first-match chain where every rule must apply (that is a pipeline or a plain list).
- **When not to use** — The steps and their order never change; a lookup by key (a map) picks the
  handler; every step always runs (a loop over a list is simpler).
- **Related patterns** — Chain of Responsibility, Command, Mediator and Observer are different ways to
  connect senders and receivers: a chain passes a request along until someone handles it, Command
  creates one-way links, Mediator centralises communication, Observer lets receivers subscribe
  dynamically; chains often run up a Composite's parent links; handlers can be Commands; the
  structure resembles Decorator, but handlers may stop the request and decorators may not (S10).
- **Common combinations** — Composite; Command; Template Method in a base handler.
- **Refactoring opportunities** — Toward: long `if / else if` ladders over request properties that
  choose processing. Away: a chain whose handlers always all run in a fixed order — use a list.
- **Testing considerations** — Test each handler alone (handles or passes); test the assembled order;
  test the unhandled path explicitly (DES-PAT-05).
- **Security considerations** — Security chains fail closed: if no handler grants access, deny
  (SEC-DESIGN-02, SEC-ERR-01); order matters (authenticate before authorising, validate before
  processing).
- **Language and framework considerations** — Servlet filters, the Spring Security filter chain,
  Express/Koa/ASP.NET middleware and Laravel middleware and `Pipeline` are pipeline-style chains;
  Go `http.Handler` middleware has a decorator's shape — classify by whether a link can stop the
  request (T-27). See `frameworks.md`.
- **Source provenance** — S10 https://refactoring.guru/design-patterns/chain-of-responsibility ·
  direct. S9 Ch.27 agrees on intent, problem, solution and structure but is cut off; its Q&A adds
  unhandled requests and debugging difficulty, consistent with S10. Example, misuses, testing,
  security and framework notes: extension (X14).
