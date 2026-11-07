# Python (incl. Django, Flask, FastAPI)

Conventions: PEP 8, PEP 20, PEP 257, PEP 484 typing, framework docs (X11).

## Identify
- `pyproject.toml` (PEP 621; tool configs for ruff/black/mypy/pytest), `requirements*.txt`,
  `setup.cfg`, `Pipfile`; lockfiles (`poetry.lock`, `uv.lock`, `requirements.lock`). Python version
  from `requires-python`, `.python-version`, CI matrix.
- Framework: Django (`manage.py`, `settings.py`, apps), Flask (`Flask(__name__)`, blueprints),
  FastAPI (`FastAPI()`, Pydantic models, dependency injection via `Depends`).

## Idioms to follow (and not flag)
- `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE` constants; formatter
  (Black/ruff format) decides layout.
- Module-level functions are fine — not everything needs a class. Duck typing and protocols over
  abstract base classes; absence of interfaces is not a DIP violation (DES-DIP-01 still applies to
  *volatile* dependencies — pass them in).
- EAFP (`try`/`except KeyError`) is idiomatic. Dataclasses/attrs/Pydantic models as plain data.
- Simple scripts and small services don't need layers (ARCH-FIT-01).

## Real issues to look for
- **Swallowed exceptions**: bare `except:` or `except Exception: pass/continue`; losing the cause —
  use `raise NewError(...) from e` (CODE-ERR-01/03).
- **Mutable default arguments** (`def f(items=[])`) — shared across calls (defect).
- **Naive datetimes**: `datetime.now()` without tz; `datetime.utcnow()` (naive, and deprecated since
  3.12) → `datetime.now(timezone.utc)` (REL-TIME-03).
- **Floats for money** → `decimal.Decimal` with explicit context/rounding (DATA-TYPE-01).
- **Resource handling** without `with` (files, locks, connections, sessions) (REL-RES-01).
- **`requests` without `timeout=`** — it waits indefinitely by default (REL-TIME-01).
- **Circular imports** worked around with local imports — usually a module-boundary problem
  (ARCH-COMP-02).
- **Django N+1**: FK/M2M access in loops/templates without `select_related`/`prefetch_related`;
  test with `assertNumQueries` (PERF-IO-01). `.all()` for large exports → `.iterator()` (PERF-IO-02).
- **Untyped public APIs** in large codebases; `Any` everywhere (DLV-SA-02).

## Security hot spots
- SQL: f-strings/`%`/`format` into `cursor.execute`; Django `raw()`/`extra()`/`RawSQL` with
  interpolation; SQLAlchemy `text()` with f-strings → bound parameters (SEC-INJ-01).
- `subprocess` with `shell=True` and input; `os.system` (SEC-INJ-02).
- `pickle.loads`, `yaml.load` without `SafeLoader`, `eval`/`exec`, `jinja2.Template(user_input)`
  (SEC-INJ-03); XML via stdlib parsers on untrusted input → `defusedxml` (SEC-INJ-04).
- `random` for tokens → `secrets` (SEC-CRYPTO-01); `requests(..., verify=False)` (SEC-CRYPTO-01);
  `tempfile.mktemp` (race-prone) → `NamedTemporaryFile`/`mkstemp`.
- Django settings: `DEBUG = True`, `ALLOWED_HOSTS = ['*']`, hard-coded `SECRET_KEY`, `CSRF_COOKIE_SECURE`
  / `SESSION_COOKIE_SECURE` off in production; `@csrf_exempt` (SEC-CONF-01, SEC-SECRET-01, SEC-CSRF-01).
- `mark_safe`/`|safe`, Flask `Markup` on user content (SEC-OUT-01). DRF views without permission
  classes, object-level checks missing in `get_object` overrides (SEC-AUTHZ-01/02).

## Testing
pytest with fixtures and `@pytest.mark.parametrize`; `monkeypatch`; time control (freezegun,
time-machine, or an injected clock); factory_boy; Hypothesis for property-based tests
(TEST-PROP-01); Django `TestCase`/pytest-django with a real database engine for query logic
(TEST-DATA-01); mutmut for mutation testing of critical modules (TEST-MUT-01); pytest-benchmark
for microbenchmarks (TEST-PERF-01); Atheris for fuzzing parsers (TEST-FUZZ-01).
Migrations: Django runs each migration in a transaction on PostgreSQL — set `atomic = False` for
`AddIndexConcurrently`, keep `RunPython` backfills out of schema migrations or make them batched
and idempotent, and never import application models into migrations (use `apps.get_model`)
(DATA-MIG-02, DATA-MIG-03).

## Tools
ruff (lint + format), mypy/pyright (types), bandit (security lint), pip-audit (advisories),
radon/xenon (complexity), vulture (dead code), import-linter (layer contracts), coverage.py.
