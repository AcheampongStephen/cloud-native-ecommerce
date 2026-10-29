# Troubleshooting

| Symptom | Evidence to collect | Action |
|---|---|---|
| Docker engine unavailable | `docker version`, Docker Desktop engine status | Start Docker Desktop's Linux engine; do not change application credentials |
| Port 8007 already used | `Get-NetTCPConnection -LocalPort 8007` | Stop the other known dev instance or change published host port |
| Missing secret variable | Compose validation error | Run initializer; compare variable names with .env.example without sharing values |
| PostgreSQL password failure | Service logs, whether volumes predate .env | Restore original credentials; changing .env does not rotate existing database roles |
| Readiness 503 | Service logs and migration status | Check DB connectivity; run migrations with the owning service configuration |
| Checkout 503 / pending | Order ID, original retry key, dependency health | Resume from My orders; do not invent a new checkout key |
| No confirmation | Pending outbox, worker logs, RabbitMQ queue counts | Restore broker/consumer; duplicate delivery is safe |
| Declined payment | Order status and stock before/after | Select approve for a new simulated purchase; no real funds moved |
| Insufficient stock | `/api/v1/inventory/{id}` | Inspect previous orders/reservations; admin can make deliberate stock adjustment |
| 401 after reload | Browser session status | Sign in again; tokens intentionally are not persisted |
| Native test clients stall in managed sandbox | Test runner stops at first HTTP call | Run tests in a permitted local shell; Windows sandbox loopback restrictions can block event-loop setup |

Diagnose using actual errors and request IDs. Never paste .env, Authorization
headers, database URLs containing passwords, or password hashes into an issue.
Native logs stream to the starting terminal. Compose logs are available with
`docker compose logs --tail=100 SERVICE`. Fix the dependency before retrying a
pending order. See the recovery runbooks for deeper incident procedures.
