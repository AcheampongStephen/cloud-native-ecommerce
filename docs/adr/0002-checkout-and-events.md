# ADR 0002: Resumable checkout and transactional outbox

Status: accepted.

Decision: persist pending order before remote side effects, use user-scoped
idempotency keys and idempotent Inventory/Payment operations, serialize aggregate
coordination, then save final state and event atomically. Publish events at least
once with consumer deduplication.

Why: retries after lost responses must not double-charge or decrement stock twice.
A direct publish after committing an order can lose notifications on process crash.

Tradeoffs: synchronous coordination holds an order-local DB transaction while
dependencies respond. Native SQLite serializes all order writers. There is no
automatic reconciler, expiry, provider refund or distributed transaction. A future
durable workflow worker should own scheduled retry/reconciliation at higher scale.
