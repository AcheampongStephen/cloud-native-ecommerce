# Monitoring and observability

Implemented: JSON request logs with service, generated request ID, method, path,
status and duration_ms; dependency/database error responses; liveness/readiness
endpoints; Compose API and infrastructure healthchecks; worker reconnect logs.
Passwords, tokens, and bodies are not intentionally logged by application handlers.

Request IDs are currently generated per hop, not propagated end-to-end tracing.
OpenTelemetry's API package is a framework dependency, not configured trace export.
Prometheus, Grafana, Loki, metrics endpoints, CloudWatch and trace collection are
not implemented. Do not infer them from the original training roadmap.

Suggested operational signals before any real deployment:

- Checkout success ratio and latency, split by business decline versus outage.
- Count/age of pending orders and oldest unsent outbox event.
- Queue depth, oldest message, dead letters, consumer acknowledgement rate.
- DB errors, lock waits, stock conflicts, authentication failure rate.
- Backup freshness and restore verification.

No SLO is claimed. Define a measurement window, traffic profile and data source
before setting targets. API readiness checks local schema access, not worker
progress or the full purchase journey; run the smoke test for end-to-end evidence.
