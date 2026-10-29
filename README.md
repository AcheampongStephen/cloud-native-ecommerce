# Common Goods — Cloud-Native Commerce

[GitHub repository](https://github.com/AcheampongStephen/cloud-native-ecommerce) ·
[CI checks](https://github.com/AcheampongStephen/cloud-native-ecommerce/actions)

A complete local e-commerce demonstration: storefront, API gateway, identity,
catalog, inventory, order coordination, simulated payments, and notifications.
Built with Python/FastAPI, PostgreSQL, SQLAlchemy/Alembic, and RabbitMQ.

**Local development application, not a validated production system.**
No real payments, card data, shipping, tax, or email provider integrations.

## Run with Docker Desktop (recommended)

Open PowerShell in this repository. Start Docker Desktop with its Linux engine.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m commerce.manage init
docker compose up --build -d --wait --wait-timeout 180
```

Open **http://127.0.0.1:8007**. Create an account with a password of at least
12 characters, add goods to your bag, and place a demo order. The payment
selector can simulate approval or decline. Confirmations appear under My orders.
Tokens live in browser memory; refresh signs you out. No default accounts exist.

```powershell
.\.venv\Scripts\python.exe -m scripts.smoke
docker compose ps
docker compose logs --tail=50 order order-worker notification-worker
docker compose down
```

`down` preserves database and broker volumes. **Destructive demo reset:**
`docker compose down -v` removes all Compose users, orders, stock, and messages.
Native `.data` databases are separate from Compose volumes.

## Run natively without Docker

After creating the virtual environment and installing the lock file:

```powershell
.\scripts\start.ps1
```

Or without PowerShell script execution:

```powershell
.\.venv\Scripts\python.exe -m commerce.manage init
.\.venv\Scripts\python.exe -m commerce.manage migrate --all
.\.venv\Scripts\python.exe -m commerce.manage seed --all
.\.venv\Scripts\python.exe -m scripts.dev
```

Native mode uses separate SQLite files and a local outbox-to-inbox relay.
Compose uses PostgreSQL databases with separate roles and real RabbitMQ.
Ctrl+C stops all native child processes. Do not run both modes on port 8007.
Native APIs: identity 8001, product 8002, inventory 8003, payment 8004,
order 8005, notification 8006, gateway/frontend 8007. Each API has `/docs`.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
node --check frontend/app.js
.\.venv\Scripts\python.exe -m scripts.smoke
```

Smoke tests create isolated demo accounts and consume one unit of stock per run.
Unit/API tests use isolated temporary databases. Optional PostgreSQL tests use
`TEST_POSTGRES_URL` and create/drop uniquely named test schemas.

To run PostgreSQL tests in an isolated disposable container after building the app:

```powershell
docker compose -f compose.test.yaml run --rm tests
docker compose -f compose.test.yaml down
```

## Repository

```text
commerce/       Service application factory, routes, storage, workers, admin CLI
frontend/       Accessible responsive storefront, no frontend build step
migrations/    Versioned service-local Alembic schema
scripts/       PowerShell startup, process supervisor, smoke test, DB initialization
tests/         API, concurrency, isolation, and lost-response recovery tests
docs/          Architecture, design, security, operations, learning progress
.github/       CI for SQLite/PostgreSQL tests, audit, and Compose smoke test
```

Services run independently but share one versioned source package and image in
this monorepo. This simplifies local maintenance; it is not independent service
release versioning. Each process selects its routes using `SERVICE` and owns its
database. No runtime service queries another service's tables.

Redis is deliberately omitted: no measured caching requirement exists.
AWS, Terraform, Kubernetes, GitOps, dashboards, and external hosting are future
delivery work, not included application capabilities. Nothing provisions AWS.

Start with [setup](docs/setup-guide.md), [architecture](docs/architecture.md),
[API reference](docs/api-documentation.md), [security](docs/security.md),
[troubleshooting](docs/troubleshooting.md), and [progress](docs/progress.md).
