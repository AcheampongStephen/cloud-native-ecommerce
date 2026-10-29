"""Local administration. No network provisioning or embedded credentials."""

import argparse
import getpass
import hashlib
import os
import secrets
from pathlib import Path

from alembic import command
from alembic.config import Config

from commerce.catalog import PRODUCTS
from commerce.config import SERVICES, Settings
from commerce.db import Record, Stock, database
from commerce.security import hash_password


def migrate(settings):
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = settings.database_url
    try:
        command.upgrade(Config("alembic.ini"), "head")
    finally:
        if old is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old


def seed(settings):
    engine, sessions = database(settings.database_url)
    with sessions() as session, session.begin():
        if settings.service == "product":
            for product in PRODUCTS:
                key = "product:" + product["id"]
                if not session.get(Record, key):
                    session.add(Record(id=key, kind="product", data=product))
        elif settings.service == "inventory":
            for product in PRODUCTS:
                if not session.get(Stock, product["id"]):
                    session.add(Stock(product_id=product["id"], available=25))
    engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["init", "migrate", "seed", "admin"])
    parser.add_argument("--all", action="store_true", help="Native local databases only")
    args = parser.parse_args()
    if args.action == "init":
        path = Path(".env")
        if path.exists():
            print(".env already exists; preserving existing credentials")
            return
        path.write_text(
            "JWT_SECRET="
            + secrets.token_urlsafe(48)
            + "\nINTERNAL_SECRET="
            + secrets.token_urlsafe(48)
            + "\nPOSTGRES_PASSWORD="
            + secrets.token_hex(24)
            + "\nRABBIT_PASSWORD="
            + secrets.token_hex(24)
            + "\n"
            + "".join(
                f"{name.upper()}_DB_PASSWORD={secrets.token_hex(24)}\n"
                for name in SERVICES
                if name != "gateway"
            ),
            encoding="utf-8",
        )
        print("Generated .env. Keep this file private and out of Git.")
        return
    if args.all and os.getenv("DATABASE_URL"):
        raise SystemExit("--all is only for native mode; unset DATABASE_URL first")
    names = SERVICES if args.all else [os.getenv("SERVICE", "gateway")]
    for name in names:
        settings = Settings.from_env(name)
        if args.action == "migrate":
            migrate(settings)
        elif args.action == "seed":
            seed(settings)
        else:
            if name != "identity" or args.all:
                raise SystemExit("Set SERVICE=identity before creating an administrator")
            email = input("Admin email: ").strip().lower()
            password = getpass.getpass("Password (12+ characters): ")
            from commerce.schemas import Credentials

            credentials = Credentials(email=email, password=password)
            engine, sessions = database(settings.database_url)
            with sessions() as session, session.begin():
                key = "user:" + hashlib.sha256(credentials.email.encode()).hexdigest()
                if session.get(Record, key):
                    raise SystemExit("Account exists; refusing to replace it")
                session.add(
                    Record(
                        id=key,
                        kind="user",
                        data={
                            "email": credentials.email,
                            "password_hash": hash_password(credentials.password),
                            "role": "admin",
                        },
                    )
                )
            engine.dispose()
        print(f"{name}: {args.action} complete")


if __name__ == "__main__":
    main()
