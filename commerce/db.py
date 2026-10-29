from sqlalchemy import JSON, Boolean, Integer, String, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Record(Base):
    """A service-local aggregate. Databases and credentials are isolated per service."""

    __tablename__ = "records"
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    owner: Mapped[str] = mapped_column(String(100), default="", index=True)
    data: Mapped[dict] = mapped_column(JSON)


class Stock(Base):
    __tablename__ = "stock"
    product_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    available: Mapped[int] = mapped_column(Integer)


class Outbox(Base):
    __tablename__ = "outbox"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    sent: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


def database(url):
    options = (
        {"connect_args": {"check_same_thread": False, "timeout": 30}} if url.startswith("sqlite") else {}
    )
    engine = create_engine(url, pool_pre_ping=True, **options)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def sqlite_setup(connection, _):
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=30000")

    return engine, sessionmaker(engine, expire_on_commit=False)


def lock_transaction(session, key="write"):
    # Serialize writes on SQLite; PostgreSQL paths use row locks and unique keys.
    if session.bind.dialect.name == "sqlite":
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        import hashlib
        from sqlalchemy import text

        lock_id = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big", signed=True)
        session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
