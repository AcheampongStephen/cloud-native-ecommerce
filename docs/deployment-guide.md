# Deployment scope

Supported deployment is local Docker Compose or native supervised Python.
Use README startup, verify `/health/ready`, run the smoke test, then inspect
worker logs and the inbox. Compose migrations apply at API startup; a real
deployment should run a single reviewed migration job before rolling APIs.

Updates: back up data, review migrations, rebuild with
`docker compose up --build -d --wait --wait-timeout 180`, then run smoke tests.
An older image cannot safely roll back an incompatible schema. No zero-downtime,
blue-green or canary guarantee has been implemented or measured.

No public hosting or AWS resources have been created. Before cloud deployment:
agree on account/region, threat model, managed identity, network boundaries,
secrets, TLS, costs/budgets, migrations, backups/restore, monitoring, incident
ownership, and a reviewed cleanup plan. Obtain approval before billable resources.
