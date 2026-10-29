# Cost management

The application runs locally. This implementation provisions no AWS services.
Local costs are Docker CPU/RAM, disk, electricity and downloads; stop it with
`docker compose down` when not in use. Named volumes persist until deliberately
removed. Do not use a global Docker prune command as project cleanup.

Cloud estimates require region, uptime, sizing, traffic, storage and retention.
Potentially significant costs include EKS control planes, NAT gateways, ALBs,
RDS, log ingestion/retention and cross-zone/internet transfer. No dollar estimate
is provided without those inputs and current verified pricing.

Before any cloud provisioning: review a concrete resource plan and estimate,
configure budgets/alerts (which are not a hard spending cap), label ownership,
write resource-specific cleanup, and obtain explicit approval. Prefer the local
stack until the deployment exercise justifies those expenses.
