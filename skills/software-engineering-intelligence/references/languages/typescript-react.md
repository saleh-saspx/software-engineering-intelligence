# TypeScript, JavaScript, React and Node.js

Conventions: TypeScript handbook, React docs (Rules of Hooks), typescript-eslint, Node.js docs
(X11).

## Identify
- `package.json` (dependencies, scripts, `engines`), lockfile (`package-lock.json`, `pnpm-lock.yaml`,
  `yarn.lock`), `tsconfig.json` (`strict`, `noUncheckedIndexedAccess`), ESLint config (flat
  `eslint.config.*` in ESLint 9+, or legacy `.eslintrc*`), Prettier config.
- Frameworks: React (+ Next.js, Remix, Vite), Express/Fastify/NestJS on the server.

## Idioms to follow (and not flag)
- `camelCase` values/functions, `PascalCase` components, types and classes. Prettier decides layout.
- Function components with hooks; no classes needed. Small modules of functions; no DI container
  required (NestJS is the exception — it has its own DI).
- Discriminated unions with exhaustive `switch` + `never` checks are a fine alternative to
  polymorphism (CODE-CPLX-03).
- Default vs. named exports, barrel files: team preference — follow the codebase.

## Real issues to look for
- **`any`** (explicit or implicit) and non-null assertions `!` hiding null bugs; `strict` off
  (CODE-ERR-04, DLV-SA-02). Prefer `unknown` + narrowing at boundaries; validate external data
  with a schema (Zod, Valibot, io-ts) rather than casting (SEC-VAL-01).
- **Floating promises** and swallowed rejections: un-awaited async calls, `.catch(() => {})`,
  `async` callbacks in `forEach` (CODE-ERR-01). Lint: `@typescript-eslint/no-floating-promises`.
- **React effects**: missing or wrong dependency arrays (lint `react-hooks/exhaustive-deps`);
  effects used to derive state that could be computed during render; data-fetching effects without
  cleanup/abort leading to race conditions and state updates after unmount (REL-CONC-03).
- **Rules of Hooks** violations: hooks called conditionally or in loops.
- **List keys** from array index on reorderable/dynamic lists (state attaches to the wrong item).
- **Unbounded re-renders / premature memoisation**: add `useMemo`/`useCallback`/`memo` from
  measurement, not by default (PERF-MEAS-01).
- **Money as `number`** in financial code (DATA-TYPE-01).

## Security hot spots
- `dangerouslySetInnerHTML`, `innerHTML`, `insertAdjacentHTML`, `document.write` with user data;
  `href`/`src` from user-provided URLs without scheme validation (SEC-OUT-01). Sanitise rich text
  with a maintained sanitiser (e.g. DOMPurify).
- Secrets in front-end code or public env vars — in Next.js, `NEXT_PUBLIC_*` variables are inlined
  into the browser bundle (SEC-SECRET-01, SEC-CLIENT-01). Authorisation decisions only in the client.
- Token storage: `localStorage` tokens are readable by any injected script — a risk to weigh against
  CSRF handling for cookies; report with context, not as an automatic vulnerability (SEC-CLIENT-01).
- `postMessage` handlers without `event.origin` checks (SEC-CLIENT-01).
- Next.js Server Actions and route handlers are network-reachable endpoints: authenticate and
  authorise inside them (SEC-AUTHZ-01).
- Node: template-literal SQL (`` `… ${id}` ``) → driver placeholders (`$1` in `pg`, `?` in
  `mysql2`) (SEC-INJ-01); `child_process.exec` with input (SEC-INJ-02); `eval`/`new Function`
  (SEC-INJ-03); **prototype pollution** via deep-merging request bodies (`__proto__`,
  `constructor.prototype`); **ReDoS** with user-controlled input on backtracking regexes;
  `path.join(base, userPath)` without containment checks (SEC-FILE-01); JWT verification without
  an explicit `algorithms` allow-list (SEC-SESS-01); missing body size limits; missing security
  headers (helmet) and permissive CORS (SEC-CONF-01).

## Testing
Vitest or Jest; Testing Library — query by role/label/text and assert what users see, not
component internals (TEST-BEH-01); MSW for network mocking at the boundary (TEST-BEH-02);
Playwright or Cypress for a few E2E journeys; supertest for HTTP handlers; fast-check for
property-based tests (TEST-PROP-01); Stryker for mutation testing of critical modules
(TEST-MUT-01). Watch for committed `.only`/`.skip` (TEST-SKIP-01) — `scripts/test_smells.py` finds
them.

## Tools
`tsc --noEmit`, ESLint with typescript-eslint, eslint-plugin-react-hooks, eslint-plugin-security;
Prettier; `npm audit`/`pnpm audit` (advisories); knip or ts-prune (dead code); dependency-cruiser
(architecture rules) and madge (cycles).
