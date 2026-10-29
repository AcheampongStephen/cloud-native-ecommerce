# Docker operation

`docker compose up --build -d --wait --wait-timeout 180` builds the gateway image
once and reuses it for independently running services and workers. This avoids
parallel build exports racing to overwrite the same image tag.

Dockerfile stages:

- Python 3.13 slim Bookworm builder creates a virtual environment and installs
  the complete dependency lock without pip's download cache.
- Runtime stage copies that environment and only application/migration/frontend
  files, creates UID/GID 10001, and runs without root privileges.
- PATH selects the virtual environment; unbuffered output supports container logs.
- Healthcheck probes local readiness. Workers use a recent broker-loop heartbeat
  instead of an HTTP probe; this does not prove end-to-end message progress.
- Startup applies Alembic, inserts missing seed data, then execs the API runner.

Compose keeps PostgreSQL and RabbitMQ storage in named volumes. Only gateway
port 8007 is published, on 127.0.0.1. Application containers drop capabilities
and disallow privilege escalation. Secrets come from ignored `.env`, not images.
`.dockerignore` excludes local credentials, databases, Git, and the host venv.

```powershell
docker compose ps
docker compose logs --tail=80 gateway order inventory
docker compose restart order-worker notification-worker
docker compose down
```

`docker compose down -v` is a destructive demo reset, not ordinary shutdown.
It deletes named database/message volumes. Back up first if data matters.

Python, PostgreSQL, and RabbitMQ images use controlled minor/major tags; these
tags can change. Capture verified image digests and scan them before a release.
The runtime image currently includes test/lint dependencies from the shared lock;
split runtime/tooling locks before optimizing a deployed image. Docker Desktop
resource usage and disk space are local costs; no cloud resource is created.
