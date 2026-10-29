# Database design

Alembic revision 0001 creates the same storage shape in each independent service
database. The generic aggregate approach is a demo tradeoff; ownership is enforced
by process configuration, credentials, and APIs, not shared cross-service joins.

| Table | Columns / purpose |
|---|---|
| records | id PK, kind indexed, owner indexed, data JSON |
| stock | product_id PK, available integer with nonnegative check |
| outbox | id PK, payload JSON, sent indexed |
| alembic_version | Applied schema revision |

Identity records: email-derived unique ID, salted password hash, role.
Product records: stable ID, description, category, integer price, display emoji.
Inventory records: idempotent reservations with reserved/committed/released state.
Payment records: immutable per-order simulated decision and original request.
Order records: owner, original request, retry key, item price snapshots, lifecycle.
Notification records: unique originating event ID and local delivery result.

One PostgreSQL server contains identity/product/inventory/payment/order/notification
databases. Application roles own only their database. PUBLIC database connection
permission is revoked on these databases. The initialization administrator is
used only by the database container setup and operational commands.

Money uses cents; quantities are positive integers. Stock changes and reservation
records commit atomically. All lines roll back if any stock decrement fails.
Order final state and outbox record commit in one order-local transaction.

Migrations run with `python -m commerce.manage migrate` for SERVICE and DATABASE_URL.
Native `--all` migrates each local database. Startup does not call create_all.
Use a dedicated migration job and narrower runtime privileges in production;
current application roles can alter their own schemas for local startup.
Do not run concurrent migrations against the same database. The current schema
has no foreign keys or typed domain columns inside JSON; add constraints and
carefully reviewed migrations as the domain grows.
