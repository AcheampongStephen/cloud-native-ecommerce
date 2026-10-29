# Delayed notifications

1. Confirm the order is confirmed, not pending or declined.
2. Inspect `docker compose logs --tail=80 order-worker notification-worker rabbitmq`.
3. Check `docker compose exec rabbitmq rabbitmqctl list_queues name messages consumers`.
4. Inspect unsent outbox rows through the order database using operator tooling;
   do not change sent flags while a publisher is running.
5. Restore broker/database connectivity, then restart the failed worker if needed.
6. Verify the owner's inbox. The consumer deduplicates repeated event IDs.
7. Investigate commerce.dead entries as malformed events; do not blindly requeue
   poison messages. A worker running without progress requires investigation.

Publisher confirmation precedes the sent flag. Consumer DB commit precedes ack.
Both crash windows can cause duplicate deliveries, which the inbox handles.
