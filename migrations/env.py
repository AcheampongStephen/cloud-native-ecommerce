from alembic import context

from commerce.config import Settings
from commerce.db import Base, database

engine, _ = database(Settings.from_env().database_url)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
