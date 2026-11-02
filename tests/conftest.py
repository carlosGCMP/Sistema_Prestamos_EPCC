import os
from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CreateSchema, DropSchema

import app.infrastructure.models  # noqa: F401
from app.infrastructure.database import Base, get_session
from app.main import app as api


@pytest.fixture
def session_factory() -> Generator[sessionmaker[Session]]:
    if database_url := os.environ.get("EPCC_TEST_DATABASE_URL"):
        admin_engine = create_engine(database_url)
        if admin_engine.dialect.name != "postgresql":
            raise ValueError("EPCC_TEST_DATABASE_URL debe apuntar a PostgreSQL")
        schema = f"epcc_test_{uuid4().hex}"
        with admin_engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        engine = create_engine(database_url, connect_args={"options": f"-csearch_path={schema}"})
        try:
            Base.metadata.create_all(engine)
            yield sessionmaker(bind=engine, expire_on_commit=False)
        finally:
            engine.dispose()
            with admin_engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
            admin_engine.dispose()
        return
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient]:
    def override_session() -> Generator[Session]:
        with session_factory() as session:
            yield session
            session.commit()

    api.dependency_overrides[get_session] = override_session
    with TestClient(api) as test_client:
        yield test_client
    api.dependency_overrides.clear()
