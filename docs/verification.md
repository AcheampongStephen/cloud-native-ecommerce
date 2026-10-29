# Verification evidence

Validated locally on 2026-10-29 using Windows PowerShell, Python 3.13 and Docker
Desktop's Linux engine.

| Check | Result |
|---|---|
| SQLite API/security/failure/concurrency suite | 13 passed |
| Same suite against isolated PostgreSQL schemas | 13 passed |
| Docker/PostgreSQL/RabbitMQ customer journey | Passed |
| Native SQLite/local-relay customer journey | Passed on offset ports 8101–8107 |
| Dependency audit of complete application lock | No known vulnerabilities found at audit time |
| Python lint and formatting | Passed |
| Installed dependency consistency (`pip check`) | Passed |
| JavaScript syntax | Passed |
| Browser catalog category filtering | Audio displayed two matching products |
| Browser cart | One headphone item displayed a $129.00 subtotal |
| Compose startup readiness | APIs, PostgreSQL, RabbitMQ and both workers healthy |
| Secret/data ignore checks | .env, .data, and .venv excluded from Git |

Tests cover password salting, registration/validation, authentication, role checks,
owner isolation, catalog updates, health endpoints, idempotent successful checkout,
decline compensation, atomic multiline stock rollback, concurrent reservations,
duplicate notification delivery and response loss after payment/commit/release.
Each test fixture applies Alembic migrations to isolated databases/schemas.

Both live smoke tests exercise registration, login, catalog, a declined payment
with stock release, approved checkout, identical request replay, stock deduction,
order history and eventual local-inbox notification. Docker mode uses real
RabbitMQ; native mode uses the explicitly different local relay.

One non-failing deprecation warning remains: the updated Starlette TestClient
supports httpx for now but recommends its newer client backend. No warning is
suppressed. These local checks preceded GitHub publication; see the repository's
Actions tab for current remote workflow results. No browser-authentication, performance/load, external security,
container vulnerability, cloud, Kubernetes or full backup-restore validation is
claimed. See security.md and progress.md for outstanding work.
