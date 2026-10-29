# API reference

Public paths use `/api/v1`. JSON requests reject unknown fields. The gateway
forwards Authorization, Content-Type, and Idempotency-Key only. It cannot forward
service credentials. Authorization is enforced by the owning service.

| Method | Path | Access / result |
|---|---|---|
| POST | `/auth/register` | Public; email, password (12–128 characters); creates customer |
| POST | `/auth/login` | Public; credentials; returns 30-minute bearer token |
| GET | `/auth/me` | Authenticated; current account |
| GET | `/products` | Public; q, category, offset, limit; items + total |
| GET | `/products/{id}` | Public; one product |
| PUT | `/products/{id}` | Admin; id, name, description, category, price_cents, emoji |
| GET | `/inventory/{id}` | Public; available count |
| PUT | `/inventory/{id}` | Admin; available (nonnegative integer) |
| POST | `/orders` | Authenticated; Idempotency-Key required; checkout result |
| GET | `/orders` | Authenticated; only current user's orders |
| GET | `/orders/{id}` | Owner only; another owner's ID returns 404 |
| GET | `/notifications` | Authenticated; only current user's local inbox |

Checkout example (the only payment methods are simulated):

```json
{"items":[{"product_id":"keyboard","quantity":1}],"payment_method":"approve"}
```

Use an 8–100 character `Idempotency-Key` header, normally a UUID. Retain the key
and original payload on 503 or a lost response. Successful HTTP 200 can represent
`confirmed`, `declined`, or `rejected`: inspect `status`. A different request with
the same key returns 409. Existing order responses include owner-visible request
and retry_key to allow resuming pending checkout after a browser refresh.

Internal routes require `X-Internal-Key` and are unavailable through the gateway:

- POST `/internal/reservations/{order_id}` with items.
- POST `/internal/reservations/{order_id}/commit` or `/release`.
- POST `/internal/payments/{order_id}` with amount_cents and method.

Each API exposes `/docs`, `/openapi.json`, `/health/live`, and `/health/ready`.
The gateway's OpenAPI describes the proxy, not all downstream request schemas.
Use the individual service docs in native mode; Compose service ports are private.
Readiness checks service-local schema access, not all downstream dependencies or
workers. Authentication failures return 401, role failures 403, missing resources
404, conflicts 409, input failures 422, and dependency/database failures 503.
