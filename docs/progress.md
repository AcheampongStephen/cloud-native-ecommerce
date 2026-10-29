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

See verification.md for final test evidence and its limits. Workflow definitions
exist locally; GitHub checks have not been run on a remote repository.

## Outstanding delivery milestones

- Review application with the user and exercise incident recovery.
- Choose a GitHub destination and configure branch protection.
- Independent release packaging, richer typed domain schemas, automatic pending
  reconciliation, rate limiting and external identity for public deployment.
- Container/IaC security scans, SBOM artifacts, local Kubernetes/Helm, Terraform,
  approved AWS environment, GitOps, telemetry stack and restore drills.

No AWS resources are provisioned. Implementation completion is not evidence that
the user has completed the apprenticeship assessments or acquired every listed skill.
