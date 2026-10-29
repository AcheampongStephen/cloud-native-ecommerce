# ADR 0001: Complete local platform with two infrastructure modes

Status: accepted.

Context: the user changed the initial lesson-by-lesson request to ask for the
whole application. The workspace was empty except for Git metadata.

Decision: implement all requested local business components, a simple storefront,
and tests. Use independent FastAPI processes with service-owned databases. Ship
Compose with PostgreSQL/RabbitMQ and a lighter SQLite/local-relay native mode.
Keep one package/image to make Windows setup and maintenance approachable.

Alternatives: separate repositories/images provide stronger release independence
but increase setup overhead; a monolith simplifies transactions but provides fewer
distributed failure exercises. Native-only delivery would not demonstrate a broker.

Consequences: both modes expose the same business APIs, but native relay bypasses
RabbitMQ and SQLite serializes writers. Test PostgreSQL and the broker separately.
No claim of independent release versioning or production readiness.
