"""At-least-once delivery: transactional outbox -> RabbitMQ -> durable inbox."""

import json
import logging
import sys
import tempfile
import time
from pathlib import Path

import pika
from sqlalchemy import select

from commerce.basic_routes import accept_notification
from commerce.config import Settings
from commerce.db import Outbox, database

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("worker")
QUEUE = "commerce.notifications"
HEARTBEAT = Path(tempfile.gettempdir()) / "commerce-worker-heartbeat"


def connect(url):
    parameters = pika.URLParameters(url)
    parameters.heartbeat = 30
    parameters.blocked_connection_timeout = 10
    parameters.socket_timeout = 5
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue="commerce.dead", durable=True)
    channel.queue_declare(
        queue=QUEUE,
        durable=True,
        arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": "commerce.dead"},
    )
    return connection, channel


def publish_batch(sessions, url):
    connection, channel = connect(url)
    try:
        channel.confirm_delivery()
        with sessions() as session:
            events = session.scalars(select(Outbox).where(Outbox.sent.is_(False)).limit(50)).all()
            for event in events:
                channel.basic_publish(
                    exchange="",
                    routing_key=QUEUE,
                    body=json.dumps(event.payload),
                    properties=pika.BasicProperties(
                        content_type="application/json", delivery_mode=2, message_id=event.id
                    ),
                    mandatory=True,
                )
                event.sent = True
                session.commit()
    finally:
        connection.close()


def consume(sessions, url):
    connection, channel = connect(url)
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        try:
            accept_notification(sessions, json.loads(body))
        except (ValueError, KeyError, TypeError):
            log.error(json.dumps({"event": "invalid_notification_dead_lettered"}))
            ch.basic_nack(method.delivery_tag, requeue=False)
        except Exception:
            # Close connection: unacknowledged delivery returns to the queue after reconnect.
            log.exception("notification storage failed")
            raise
        else:
            ch.basic_ack(method.delivery_tag)

    channel.basic_consume(queue=QUEUE, on_message_callback=callback)
    try:
        while connection.is_open:
            connection.process_data_events(time_limit=1)
            HEARTBEAT.touch()
    finally:
        if connection.is_open:
            connection.close()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "health":
        healthy = HEARTBEAT.exists() and time.time() - HEARTBEAT.stat().st_mtime < 30
        raise SystemExit(0 if healthy else 1)
    settings = Settings.from_env()
    if settings.service not in ("order", "notification") or not settings.rabbit_url:
        raise SystemExit("Worker requires SERVICE=order|notification and RABBIT_URL")
    _, sessions = database(settings.database_url)
    while True:
        try:
            if settings.service == "order":
                publish_batch(sessions, settings.rabbit_url)
                HEARTBEAT.touch()
                time.sleep(2)
            else:
                consume(sessions, settings.rabbit_url)
        except KeyboardInterrupt:
            break
        except Exception:
            log.exception("worker failure; reconnecting in 5 seconds")
            time.sleep(5)


if __name__ == "__main__":
    main()
