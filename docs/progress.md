# Project progress

## Implemented

- Seven independently running API processes including gateway; static frontend.
- Customer registration/login, expiring JWTs, admin checks and owner isolation.
- Catalog search/filtering, inventory management/reservations, order history.
- Simulated approve/decline payments, idempotent checkout and pending recovery.
- Transactional outbox, RabbitMQ publisher/consumer, deduplicated local inbox.
- Separate PostgreSQL databases/roles, Alembic migration, native SQLite fallback.
- Docker Compose, non-root image, native supervisor, smoke and API tests.
- GitHub Actions workflow and operating/design/security documentation.

## Validation

See verification.md for local test evidence and its limits. The repository is
published to GitHub; current remote check results are available under its Actions tab.

## Outstanding delivery milestones

- Review application with the user and exercise incident recovery.
- Configure GitHub branch protection and required checks.
- Independent release packaging, richer typed domain schemas, automatic pending
  reconciliation, rate limiting and external identity for public deployment.
- Container/IaC security scans, SBOM artifacts, local Kubernetes/Helm, Terraform,
  approved AWS environment, GitOps, telemetry stack and restore drills.

No AWS resources are provisioned. Implementation completion is not evidence that
the user has completed the apprenticeship assessments or acquired every listed skill.
