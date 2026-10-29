"""Supervise native services and deliver local notifications without external infrastructure."""

import os
import signal
import subprocess
import sys
import time

from sqlalchemy import select

from commerce.basic_routes import accept_notification
from commerce.config import PORTS, SERVICES, Settings
from commerce.db import Outbox, database


def main():
    if os.getenv("DATABASE_URL"):
        raise SystemExit("Native mode requires DATABASE_URL to be unset")
    children = []
    engines = []
    offset = int(os.getenv("PORT_OFFSET", "0"))
    try:
        for name in SERVICES:
            env = {**os.environ, "SERVICE": name}
            children.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "commerce.app:create_app",
                        "--factory",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(PORTS[name] + offset),
                    ],
                    env=env,
                )
            )
        print(f"Storefront: http://127.0.0.1:{8007 + offset} — Ctrl+C stops all services", flush=True)
        order_engine, order_sessions = database(Settings.from_env("order").database_url)
        notification_engine, notification_sessions = database(Settings.from_env("notification").database_url)
        engines.extend([order_engine, notification_engine])
        while all(child.poll() is None for child in children):
            with order_sessions() as session:
                for event in session.scalars(select(Outbox).where(Outbox.sent.is_(False))).all():
                    accept_notification(notification_sessions, event.payload)
                    event.sent = True
                    session.commit()
            time.sleep(1)
        raise RuntimeError("A service exited; see its output above")
    except KeyboardInterrupt:
        pass
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        for engine in engines:
            engine.dispose()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    main()
