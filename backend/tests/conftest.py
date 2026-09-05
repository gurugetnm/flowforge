"""Shared pytest fixtures.

Tests run against a real PostgreSQL database so JSONB columns, foreign keys
and cascades behave exactly as they do in production. Point
``TEST_DATABASE_URL`` at a scratch database; its schema is rebuilt from the
Alembic migrations once per session.
"""

import os
from collections.abc import Generator

import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from alembic import command

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://flowforge:flowforge@localhost:5432/flowforge_test",
)

# Applied before app modules read settings, so the engine and Alembic both
# target the scratch database.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-used-in-production")


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    """Session wide engine with a schema built from the migration history."""
    engine = create_engine(TEST_DATABASE_URL, poolclass=None, future=True)

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")

    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Generator[Session, None, None]:
    """A session bound to a transaction that is rolled back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, autoflush=False, expire_on_commit=False)
    db = factory()

    try:
        yield db
    finally:
        db.close()
        # A failed statement (an expected IntegrityError, say) already ended
        # the transaction, so only roll back when one is still open.
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def alembic_config() -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return config


@pytest.fixture
def clean_database(engine: Engine) -> Generator[None, None, None]:
    """Truncate all data tables. For tests that need to commit."""
    yield
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE users, workflows, workflow_nodes, workflow_edges, "
                "executions, execution_nodes RESTART IDENTITY CASCADE"
            )
        )
