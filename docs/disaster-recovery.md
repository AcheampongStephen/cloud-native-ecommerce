# Backup and recovery

Native mode: stop the supervisor before copying the complete `.data` directory
to private backup storage. SQLite WAL files can be required while a database is
open; do not copy only a live .db file and assume consistency. Use SQLite backup
APIs for an online backup workflow.

Compose mode: take PostgreSQL logical backups and preserve the private .env
credentials separately in secure storage. PowerShell native-command redirection
can alter binary streams, so create dumps inside the database container and copy
them as files instead:

```powershell
docker compose exec -T postgres sh -c 'pg_dumpall -U platform_admin > /tmp/common-goods.sql'
docker compose cp postgres:/tmp/common-goods.sql ./.data/common-goods.sql
```

The dump contains sensitive account/role data. Do not commit or share it. It is
a logical cluster dump including role definitions; restore into a separate fresh
test PostgreSQL cluster as an administrator and resolve role/database conflicts
deliberately. This task has not validated a full disaster-recovery restore drill.

RabbitMQ durability protects restart scenarios when its volume survives, not
loss of the volume. Outbox events marked sent are not automatically replayed if
the broker volume is destroyed before delivery. Retain backups or design an
operator-controlled event replay from retained outbox records with idempotent
consumers. No measured RPO/RTO or high-availability guarantee exists.
