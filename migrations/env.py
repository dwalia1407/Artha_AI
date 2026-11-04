"""Alembic environment. The database URL comes from the app config (DATABASE_URL)."""

from alembic import context
from sqlalchemy import create_engine

from app.config import Config, normalize_database_url
import app.models  # noqa: F401  (registers tables on the metadata)
from app.extensions import db

target_metadata = db.metadata
url = normalize_database_url(Config.SQLALCHEMY_DATABASE_URI)


def run_migrations_offline():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=url.startswith("sqlite"))
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
